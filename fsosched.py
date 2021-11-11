import json
import random
import re
from graphics import *

class Policy:
    def __init__(self, type, preemptive):
        self.preemptive = preemptive
        self.type = type
        if type == "Priority":
            self.comp = lambda ta, tb: ta.get_priority() - tb.get_priority()
        elif type == "SJF":
            self.comp = lambda ta, tb: ta.get_burst() - tb.get_burst()
        elif type == "FIFO":
            self.comp = lambda ta, tb: 1
        elif type == "SRTF":
            self.comp = lambda ta, tb: ta.get_remaining_time() - tb.get_remaining_time()
        else:
            rrm = re.match(r"RR ([0-9]+)", type)
            if rrm:
                self.comp = lambda ta, tb: 1
                self.quantum = int(rrm.group(1))
                  
class Task:
    def get_burst(self) -> int:
        return -1
    
    def get_remaining_time(self) -> int:
        return -1
    
    def get_priority(self) -> int:
        return self.priority
    
    def set_priority(self, priority : int):
        self.priority = priority                  
  
class Queue(Task):
    def __init__(self, dictionary : dict):
        self.set_priority(dictionary.get("priority", 0))
        
        self.queue = list()
        self.active = None
        
    def get_burst(self) -> int:
        pass
    
    def get_remaining_time(self) -> int:
        pass

    def is_empty(self):
        pass
    
class Process(Task):
    def __init__(self, dictionary : dict):
        self.set_priority(dictionary.get("priority", 0))
        
class Consumer:
    def __init__(self):
        pass