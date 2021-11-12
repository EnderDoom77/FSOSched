import json
import random
import re
from graphics import *
from typing import List, Dict

class Policy:
    def __init__(self, type : str, preemptive : bool):
        self.preemptive : bool = preemptive
        self.type : str = type
        if type == "Priority":
            self.comp = lambda ta, tb: ta.priority - tb.priority
        elif type == "SJF":
            self.comp = lambda ta, tb: ta.get_burst() - tb.get_burst()
        elif type == "FIFO":
            self.comp = lambda ta, tb: 1
        elif type == "FILO":
            self.comp = lambda ta, tb: -1
        elif type == "SRTF":
            self.comp = lambda ta, tb: ta.get_remaining_time() - tb.get_remaining_time()
        else:
            rrm = re.match(r"RR ([0-9]+)", type)
            if rrm:
                self.type = "RR"
                self.comp = lambda ta, tb: 1
                self.quantum = int(rrm.group(1))
                
    def insert(self, task : Task, task_list : List[Task]) -> int:
        starts = 0 if self.preemptive else 1
        for i in range(starts, len(task_list)):
            if self.comp(task, task_list[i]) < 0:
                task_list.insert(i, task)
                return i
        task_list.append(task)
        return len(task_list) - 1
    
    def should_preempt(self, queue : Queue) -> bool:
        if self.type == "RR":
            return queue.bursts_since_last >= self.quantum and len(queue.tasks) > 1
        else:
            return False
            
                  
class Task:
    def __init__(self, name : str, priority : int, parent_queue : Queue | None = None):
        self.name = name
        self.parent_queue : Queue = parent_queue
        self.priority : int = priority
    
    def get_burst(self) -> int:
        return 1
    
    def get_remaining_time(self) -> int:
        return 1
  
class Process(Task):
    def __init__(self, dictionary : dict):
        super().__init__(dictionary.get("name", "Process"), dictionary.get("priority", 0))
        
        self.bursts : List[int] = dictionary.get("bursts", [0])
        self.queues : List[str] = dictionary.get("queues", [None])
        self.current_burst : int = 0
        self.rem_time : int = self.bursts[0]
        
        self.arrival_time : int = dictionary.get("arrival_time", 0)
        
    def get_burst(self) -> int:
        return self.bursts[self.current_burst]
    
    def get_remaining_time(self) -> int:
        return self.rem_time
        
    def get_queue_name(self) -> str:
        return self.queues[self.burst_i]
    
    def has_completed(self) -> bool:
        return self.burst_i > len(self.bursts)
    
    def burst(self) -> Process | None:
        self.rem_time -= 1
        if self.rem_time <= 0:
            self.burst_i += 1
            if not self.has_completed():
                self.rem_time = self.bursts[self.burst_i]
            
        pass # NEEDS TO BE IMPLEMENTED
  
class Queue(Task):
    def __init__(self, dictionary : dict, parent_queue = None):
        super().__init__(dictionary.get("name", "Queue"), dictionary.get("priority", 0), parent_queue)
        
        self.is_superqueue : bool = len(self._subqn) > 0
        self.subqueues : List[Queue] = [Queue(d, self) for d in dictionary.get("subqueues", [])]
        self.tasks : List[Task] = list()
        self.idle : List[Task] = list()
        self.policy : Policy = Policy(dictionary.get("mode", "FIFO"), dictionary.get("preemptive", False))
        self.bursts_since_last : int = 0
        
    def __len__(self) -> int:
        return len(self.tasks)
        
    def get_burst(self) -> int:
        p = self.get_active_process()
        if p == None: return 0
        else: return p.get_burst()
    
    def get_remaining_time(self) -> int:
        p = self.get_active_process()
        if p == None: return 0
        else: return p.get_remaining_time()
    
    def get_active_process(self) -> Process | None:
        t = self.get_active_task()
        if isinstance(t, Queue):
            return t.get_active_process()
        else:
            return t
        
    def get_active_task(self) -> Task | None:
        return self.tasks[0] if self.tasks else None        
        
    def add(self, task : Task):
        is_queue = isinstance(task, Queue)
        if not self.is_superqueue and is_queue: raise TypeError("Attempt to insert queue into non-superqueue")
        
        self.bursts_since_last = 0
        if self.is_superqueue and not is_queue: 
            subq = random.choice(self.subqueues)
            subq.add(task)
        else:
            self.policy.insert(task, self.tasks)
            task.parent_queue = self
            if self.parent_queue:
                self.parent_queue.awaken(self)
                
    def awaken(self, task : Task):
        if task in self.idle:
            self.idle.remove(task)
            self.add(task)
            if self.parent_queue:
                self.parent_queue.awaken(self)

    # suspends the active task and sends it to idle
    def suspend(self):
        self.bursts_since_last = 0
        self.idle.append(self.tasks.pop(0))
        if self.is_empty() and self.parent_queue:
            self.parent_queue.suspend()
                
    def is_empty(self) -> bool:
        return bool(self.tasks)
    
    def find_subtask(self, name : str) -> Task:
        if self.name == name: return self
        if not self.is_superqueue: return None
        for q in self.subqueues:
            n = q.find_subtask(name)
            if n: return n
    
    # Returns the completed process, if any
    def burst(self) -> Process | None:
        t = self.get_active_task()
        if t == None:
            return False
        self.bursts_since_last += 1
        proc = t.burst()
        if t is Process and proc: # if t is a completed process (self is queue)
            self.suspend()
        elif self.policy.should_preempt(self):
            self.add(self.tasks.pop(0))
            self.bursts_since_last = 0
        return proc
    
class Frame:
    def __init__(self, t: int):
        self.t = t    

config = open("config.json", "r")
d = json.load(config)
cpu_queue = Queue(config["queue_cpu"])
io_queue = Queue(config["queue_io"])

queues : Dict[str, Queue] = dict()
def extract_queues(queue : Queue):
    queues[queue.name] = queue
    for q in queue.subqueues:
        extract_queues(q)

for q in [cpu_queue, io_queue]:
    extract_queues(q)
    
suspended_processes : List[Process] = list()
for p in config["processes"]:
    suspended_processes.append(Process(p))
    
def reallocate_suspended():
    to_remove = list()
    for p in suspended_processes:
        if p.has_completed():
            to_remove.append(p) 
        elif t_now >= p.arrival_time:
            q = queues[p.get_queue_name()]
            q.add(p)
            to_remove.append(p)
    
    for p in to_remove:
        suspended_processes.remove(p)
    
t_now : int = 0
frames : list[Frame] = list()

while not(cpu_queue.is_empty() and io_queue.is_empty() and not suspended_processes):
    reallocate_suspended()
    frames.append(Frame(t_now))
    for q in [cpu_queue, io_queue]:
        if not q.is_empty() and (p := q.burst()): 
            suspended_processes.append(p)