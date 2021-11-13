import json
import random
import re
import math
from graphics import *
from typing import List, Dict

def fuse_dicts(dicts : List[dict]) -> dict:
    return {n: v for d in dicts for n, v in d.items()}

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
                
    def insert(self, task : "Task", task_list : "List[Task]") -> int:
        starts = 0 if self.preemptive else 1
        for i in range(starts, len(task_list)):
            if self.comp(task, task_list[i]) < 0:
                task_list.insert(i, task)
                return i
        task_list.append(task)
        return len(task_list) - 1
    
    def should_preempt(self, queue : "Queue") -> bool:
        if self.type == "RR":
            return queue.bursts_since_last >= self.quantum and len(queue.tasks) > 1
        else:
            return False
            
                  
class Task:
    def __init__(self, name : str, priority : int, parent_queue : "Queue | None" = None):
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
        self.color : str = dictionary.get("color", "black")
        
        self.arrival_time : int = dictionary.get("arrival_time", 0)
        
    def get_burst(self) -> int:
        return self.bursts[self.current_burst]
    
    def get_remaining_time(self) -> int:
        return self.rem_time
        
    def get_queue_name(self) -> str:
        return self.queues[self.current_burst]
    
    def has_completed(self) -> bool:
        return self.current_burst > len(self.bursts)
    
    def burst(self) -> "Process | None":
        self.rem_time -= 1
        if self.rem_time <= 0:
            self.current_burst += 1
            if not self.has_completed():
                self.rem_time = self.bursts[self.current_burst]
                
    def __str__(self) -> str:
        return f"{self.name}.{self.current_burst}({self.rem_time})"
  
class Queue(Task):
    def __init__(self, dictionary : dict, parent_queue = None):
        super().__init__(dictionary.get("name", "Queue"), dictionary.get("priority", 0), parent_queue)
        
        self.subqueues : List[Queue] = [Queue(d, self) for d in dictionary.get("subqueues", [])]
        self.tasks : List[Task] = list()
        self.idle : List[Task] = [q for q in self.subqueues]
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
        if not self.subqueues and is_queue: raise TypeError("Attempt to insert queue into non-superqueue")
        
        self.bursts_since_last = 0
        if self.subqueues and not is_queue: 
            subq = random.choice(self.subqueues)
            subq.add(task)
        else:
            pos = self.policy.insert(task, self.tasks)
            print(f"inserting process {task.name} in {self.name} (pos {pos})")
            print(f"New tasks: {self.tasks}")
            task.parent_queue = self
            if self.parent_queue != None:
                self.parent_queue.awaken(self)
                
    def awaken(self, task : Task):
        print(f"Awakening {task.name} in {self.name}")
        if task in self.idle:
            self.idle.remove(task)
            self.add(task)

    # suspends the active task and sends it to idle
    def suspend(self):
        self.bursts_since_last = 0
        self.idle.append(self.tasks.pop(0))
        if self.is_empty() and self.parent_queue != None:
            self.parent_queue.suspend()
                
    def is_empty(self) -> bool:
        return bool(self.tasks)
    
    def find_subtask(self, name : str) -> Task | None:
        if self.name == name: return self
        if not self.subqueues: return None
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
    
    def get_process_queues(self) -> List["Queue"]:
        if self.subqueues:
            return [sq for q in self.subqueues for sq in q.get_process_queues()]
        else:
            return [self]
        
    def __str__(self):
        return self.name
    
    def get_structure(self):
        if self.subqueues:
            return f"{self.name}={{{' '.join([q.get_structure() for q in self.tasks])}}}"
        else:
            return f"{self.name}={{{' '.join([p.name for p in self.tasks])}}}"
        
class GroupInfo:
    def __init__(self, q: Queue):
        self.process : Process = q.get_active_process()
        self.pt = self.process.get_remaining_time() if self.process else 0
        self.pqueues : List[Queue] = q.get_process_queues()
        self.tasks : Dict[str, List[Process]] = dict()
        for q in self.pqueues:
            pl = [p for p in q.tasks if p != self.process]
            self.tasks[q.name] = pl

class Frame:
    def __init__(self, t: int, qlist : List[Queue] = []):
        print(f"Creating frame {t}; remaining processes: {' '.join([p.name for p in suspended_processes])}")
        self.t = t
        self.groups : Dict[str, GroupInfo] = dict()
        for q in qlist:
            self.load_queue(q)
        print(f"CPU: {str(self.groups['CPU'].process)} - IO: {str(self.groups['IO'].process)} - {'; '.join([f'{p.name} in {p.parent_queue}' for p in processes])}")
        print(" - ".join([q.get_structure() for q in qlist]))
        
    def load_queue(self, q: Queue):
        self.groups[q.name] = GroupInfo(q)

class GroupRenderer:
    def __init__(self, group_frames : List[GroupInfo]):
        self.queuesizes : Dict[str, int] = dict()
        for f in group_frames:
            for n, q in f.tasks.items():
                size = len(q)
                if size > self.queuesizes.get(n, -1):
                    self.queuesizes[n] = size
        
class GraphicsInfo:
    def __init__(self, config : dict, cpuq : Queue, ioq : Queue, frames : List[Frame]):
        self.cheight = 0
        self.uwidth : int = config.get("frame_width", 20)
        self.uheight : int = config.get("item_height", 20)
        
        self.group_info : Dict[str, List[GroupInfo]] = dict()
        for f in frames:
            for gn in f.groups.keys():
                if not gn in self.group_info:
                    self.group_info[gn] = list()
                self.group_info[gn].append(f.groups[gn])
        
        self.groups = [GroupRenderer(i) for i in self.group_info.values()]
        self.queuesizes = fuse_dicts([gr.queuesizes for gr in self.groups])
        
        self.width = 2 * self.uwidth + self.get_queue_render_size(cpuq) + self.get_queue_render_size(ioq)
        
        self.cpu_levels = self.build_levels(cpuq)
        self.io_levels = self.build_levels(ioq)
        l = max(len(self.cpu_levels), len(self.io_levels))
        for lev in [self.cpu_levels, self.io_levels]:
            while len(lev) < l:
                lev.append(lev[-1])
        self.levels_depth = l
        
        self.legendlevels : List[List[str]] = list()
    
    def get_queue_render_size(self, q : Queue):
        if q.name in self.queuesizes: return self.queuesizes[q.name]
        if q.subqueues:
            v = sum([self.get_queue_render_size(sq) for sq in q.subqueues])
            self.queuesizes[q.name] = v
            return v 
        raise ValueError(f"Asked queue size of unmeasured queue: {q.name}; recognized queue names are {self.queuesizes.keys()}")
        
    def build_levels(self, rootq : Queue):
        active : Dict[Queue, int] = {rootq: self.get_queue_render_size(rootq)}
        result = [active]
        while not all([q.subqueues for q in active.keys()]):
            na = dict()
            for q in active.keys():
                if q.subqueues:
                    for sq in q.subqueues:
                        na[sq] = self.get_queue_render_size(sq)
                else:
                    na[q] = self.get_queue_render_size(q)
            active = na
            result.append(active)
            
        return result
            
        
    def get_relative_size(v : float, max : float):
        return math.sqrt(v / max)
    
    def draw_levels(self, win : GraphWin):
        x_base = 0
        for lev in [self.cpu_levels, self.io_levels]:
            self.cheight = 0
            for l in lev:
                x = x_base
                for q, size in l.items():
                    txt = Text(Point(x + size / 2, self.cheight + self.uheight / 2), q.name)
                    txt.draw(win)
                    x += size
                self.cheight += self.uheight
                    
            x_base += lev[0].values()[0] + self.uwidth
        
config_file = open("config.json", "r")
config = json.load(config_file)
cpu_queue = Queue(config["queue_cpu"])
io_queue = Queue(config["queue_io"])

queues : Dict[str, Queue] = dict()
def extract_queues(queue : Queue):
    queues[queue.name] = queue
    for q in queue.subqueues:
        extract_queues(q)

for q in [cpu_queue, io_queue]:
    extract_queues(q)

processes = list()
suspended_processes : List[Process] = list()
for p in config["processes"]:
    proc = Process(p)
    processes.append(proc)
    suspended_processes.append(proc)
    
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
    frames.append(Frame(t_now, [cpu_queue, io_queue]))
    t_now += 1
    
    finished = bool(suspended_processes)
    if finished:
        for q in [cpu_queue, io_queue]:
            if not cpu_queue.is_empty():
                finished = False
                break
            
    if finished or t_now > 100:
        break
    
    for q in [cpu_queue, io_queue]:
        if not q.is_empty() and (p := q.burst()):
            suspended_processes.append(p)
            
graph = GraphicsInfo(config["graphics"], cpu_queue, io_queue, frames)
win = GraphWin("Process Traceback", graph.width, 1000, autoflush=False)

graph.draw_levels(win)

for i in frames:
    print("printing frame!")
    win.update(15)