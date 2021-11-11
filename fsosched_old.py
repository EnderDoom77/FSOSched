import json
import random
from graphics import *

class Data:
    def __init__(self, config):
        d = json.load(config)

        self.queues = list()
        for q in d["queues"]:
            self.queues.append(Queue(self, q))
            
        for q in self.queues:
            q.load_queue(self)

        self.processes = list()
        for p in d["processes"]:
            self.processes.append(Process(p))

        self.cpu_slot = Target(True)
        self.io_slot = Target(True)

        qcpun = d["queue_cpu"]
        qion = d["queue_io"]
        qarrn = d.get("arrival_queue", qcpun)
        qcpurn = d.get("reinsertion_queue", qarrn)
        qiorn = d.get("io_reinsertion_queue", qion)
        
        self.queue_cpu = self.queues[qcpun]
        self.queue_cpu.set_target(self.cpu_slot)
        self.queue_io = self.queues[qion]
        self.queue_io.set_target(self.io_slot)
        self.queue_cpu_arrival = self.queues[qarrn]
        self.queue_cpu_reinsertion = self.queues[qcpurn]
        self.queue_io_reinsertion = self.queues[qiorn]
            
        self.frames = list()
        self.cpu_queues = self.queue_cpu.delve(self)
        self.io_queues = self.queue_io.delve(self)
        
        
        self.awaiting_ready = list()

    def execute(self):
        # check arriving processes
        # apply queue scheduling policies
        # save frame
        # execute CPU and IO cycle
        # remove completed processes from CPU and IO (into arriving processes)
            # increment burst_i and set burst_t
        pass
    
    def _flush_ready(self):
        for p in self.awaiting_ready:
            if p.burst_i == 0:
                self.queue_cpu_arrival.add_process(p)

class Target:
    def __init__(self, is_process):
        self.is_process = is_process
        self.process = None
        self.queue = None
        
    def set_p(self, process):
        temp = self.process
        self.process = process
        return temp
    
    def set_q(self, queue):
        temp = self.queue
        self.queue = queue
        return temp
                
class Queue(Process):
    def __init__(self, data, dictionary):
        self.id = len(data.queues)
        self.name = dictionary.get("name", "Queue")
        self._subqn = dictionary.get("subqueues", [])
        self.processes = list()
        self.preemptive = dictionary.get("preemptive", False)
        self.priority = dictionary.get("priority", 0)
        self.mode = dictionary.get("mode", "FIFO")
        self.quantum = dictionary.get("quantum", 1)
        
        self.target = None

        self.active_queue = None
        self.bursts_since_change = 0
        
    def load_queues(self, data):
        subq = [data.queues[i] for i in self._subqn]
        self.subqueues = list()
        for q in subq:
            self.subqueues.append(q)
            
    def set_target(self, target):
        self.target = target
        for q in self.subqueues:
            q.set_target(target)

    def execute(self):
        if self.is_empty():
            return False
        elif self.has_subqueues():
            self.execute_q()
        else:
            self.execute_p()
        self.bursts_since_change += 1
        return True

    def execute_p(self):
        if self.target.process == None:
            self.run_p()
        elif self.should_preempt_p():
            self.preempt_p()
            self.run_p()

    def should_preempt_p(self):
        if not self.preemptive: return False
        
        if self.mode == "RR":
            if self.bursts_since_change >= self.quantum:
                return True
        elif self.mode == "SRTF":
            if self.processes[0].burst_t < self.target.process.burst_t:
                return True
        elif self.mode == "Priority":
            if self.processes[0].priority < self.target.processes.burst_t:
                return True
        else:
            raise ValueError(f"Non-preemptive scheduler is using preemption: {self.mode}")
        return False

    def preempt_p(self):
        self.append(self.target.process)
        self.target.process = None
        
    def run_p(self):
        self.bursts_since_change = 0
        if not self.processes: return False
        self.target.process = self.processes[0]
        self.processes = self.processes[1:]
        return True
    
    def execute_q(self):
        if self.active_queue == None:
            self.run_q()
        elif self.should_preempt_q():
            self.preempt_q()
    
    def should_preempt_q(self):
        if not self.preemptive: return False
        
        prefq = self.preferred_subqueue()
        return prefq and prefq != self.active_queue
    
    def preempt_q():
        pass
        
    def run_q():
        pass

    def has_subqueues(self):
        return self.subqueues

    def is_empty(self):
        if self.has_subqueues():
            for q in self.subqueues:
                if not q.is_empty():
                    return False
            return True
        else:
            return len(self.processes) == 0

    def preferred_subqueue(self):
        if self.has_subqueues():
            if self.mode == "Priority":
                maxq = self.subqueues[0]
                for q in self.subqueues:
                    if maxq.is_empty() or q.priority > maxq.priority: 
                        maxq = q
                return None if maxq.is_empty() else maxq
            elif self.mode == "RR":
                
            else:
                raise ValueError(f"Unsupported scheduling policy for superqueue: {self.mode}")
        else:
            return None if len(self.processes) == 0 else self
            

    def add_process(self, process):
        if self.has_subqueues():
            random.choice(self.subqueues).add_process(process)
        else:
            if self.mode == "FIFO" or self.mode == "RR":
                self.processes.append(process)
            elif self.mode == "Priority":
                self._ins_process(process, lambda a, b : a.priority < b.priority)
            elif self.mode == "SJF":
                self._ins_process(process, lambda a, b : a.bursts[a.burst_i] < b.bursts[b.burst_i])
            elif self.move == "SRTF":
                self._ins_process(process, lambda a, b : a.burst_t < b.burst_t)
            else:
                raise ValueError(f"Unknown scheduling policy: {self.mode}")
                
    def _ins_process(self, proc, compare):
        success = False
        for i in range(len(self.processes)):
            if compare(proc, self.processes[i]):
                success = True
                self.processes.insert(i, proc)
                break
        if not success: self.processes.append(proc)
        
    def delve(self):
        if not self.has_subqueues():
            return [self]
        else:
            nested = [q.delve() for q in self.subqueues]
            return [item for sublist in nested for item in sublist]
        
    def get_active_process_queue(self):
        if not self.has_subqueues():
            return self
        else:
            q = self.active_queue
            return None if q == None else q.get_active_process_queue()
        
class Process:
    def __init__(self, dictionary):
        self.name = dictionary.get("name", "Process")
        self.priority = dictionary.get("priority", 0)
        self.bursts = dictionary.get("bursts", [0])
        self.arrival_time = dictionary.get("arrival_time", 0)

        self.burst_t = self.bursts[0]
        self.burst_i = 0
    
    # Returns whether the process has completed a cycle
    def execute(self):
        self.burst_t -= 1
        value = False
        while self.burst_t <= 0:
            self.burst_i += 1
            if self.burst_i >= len(self.bursts):
                self.burst_i = -1
                return True
            self.burst_t = self.bursts[self.burst_i]
            value = True
        return value
            
class Frame:
    def __init__(self, t):
        self.t = t
        
    def set_data(self, data):
        pass
        
       
class Render:
    def __init__(self, xsize, ysize):
        self.xsize = xsize
        self.ysize = ysize
        self.g = GraphWin("Render", xsize, ysize)
        
    def from_frames(self, data):
        pass

g = Render(1280, 720)
g.g.getMouse()
g.g.close()
