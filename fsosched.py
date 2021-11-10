import json
import random
from graphics import *

class Data:
    def __init__(self, config):
        d = json.load(config)

        self.queues = list()
        for q in d["queues"]:
            self.queues.append(Queue(self, q))

        self.processes = list()
        for p in d["processes"]:
            self.processes.append(Process(p))

        self.cpu_slot = ProcessSlot()
        self.io_slot = ProcessSlot()

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

    def execute():
        
        pass
    
    def _flush_ready(self):
        for p in self.awaiting_ready:
            if p.burst_i == 0:
                self.queue_cpu_arrival.add_process(p)

class ProcessSlot:
    def __init__(self):
        self.process = None
                
class Queue:
    def __init__(self, data, dictionary):
        self.id = len(data.queues)
        self.name = dictionary.get("name", "Queue")
        subqn = dictionary.get("subqueues", [])
        self.subqueues = [data.queues[i] for i in subqn]
        self.processes = list()
        self.preemptive = dictionary.get("preemptive", False)
        self.priority = dictionary.get("priority", 0)
        self.mode = dictionary.get("mode", "FIFO")
        self.quantum = dictionary.get("quantum", 1)
        
        self.target = None

        self.bursts_since_change = 0

    def set_target(self, target):
        self.target = target
        for q in self.subqueues:
            q.set_target(target)

    def execute(self):
        if not self.processes:
            return False
        elif self.target.process == None:
            self.run()
        elif self.preemptive:
            if self.mode == "RR":
                if self.bursts_since_change >= self.quantum:
                    self.preempt()
            elif self.mode == "SRTF":
                if self.processes[0].burst_t < self.target.process.burst_t:
                    self.preempt()
            elif self.mode == "Priority":
                if self.processes[0].priority < self.target.processes.burst_t:
                    self.preempt()
            
        self.bursts_since_change += 1

    def preempt(self):
        self.append(self.target.process)
        self.run()
        
    def run(self):
        self.bursts_since_change = 0
        if not self.processes: return False
        self.target.process = self.processes[0]
        self.processes = self.processes[1:]
        return True

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

    def preferred_queue(self):
        if self.has_subqueues():
            if self.mode == "Priority":
                maxq = self.subqueues[0]
                for q in self.subqueues:
                    if q.priority > maxq.priority:
                        maxq = q
                return maxq
            else:
                raise ValueError(f"Unsupported scheduling policy for superqueue: {self.mode}")
        else:
            return None if len(self.processes) == 0 else self
            

    def add_process(self, process, data):
        if self.has_subqueues():
            random.choice(self.subqueues).add_process(process, data)
        else:
            if self.mode == "FIFO" or self.mode == "RR":
                self.processes.append(process)
            elif self.mode == "Priority":
                self._ins_process(process, data, lambda a, b : a.priority < b.priority)
            elif self.mode == "SJF":
                self._ins_process(process, data, lambda a, b : a.bursts[a.burst_i] < b.bursts[b.burst_i])
            elif self.move == "SRTF":
                self._ins_process(process, data, lambda a, b : a.burst_t < b.burst_t)
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

class Process:
    def __init__(self, dictionary):
        self.name = dictionary.get("name", "Process")
        self.priority = dictionary.get("priority", 0)
        self.bursts = dictionary.get("bursts", [0])
        self.arrival_time = dictionary.get("arrival_time", 0)

        self.burst_t = self.bursts[0]
        self.burst_i = 0

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
