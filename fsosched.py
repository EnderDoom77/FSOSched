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
        self.completion_time : int = -1
        self.time_cost : int = sum(self.bursts)
        
    def get_burst(self) -> int:
        return self.bursts[self.current_burst]
    
    def get_remaining_time(self) -> int:
        return self.rem_time
        
    def get_queue_name(self) -> str:
        return self.queues[self.current_burst]
    
    def has_completed(self) -> bool:
        return self.current_burst >= len(self.bursts)
    
    def burst(self) -> "Process | None":
        self.rem_time -= 1
        if self.rem_time <= 0:
            self.current_burst += 1
            if not self.has_completed():
                self.rem_time = self.bursts[self.current_burst]
            return self
        return None
                
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
        
        self.color = dictionary.get("color", "#000000")
        
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
        
        if self.subqueues and not is_queue: 
            subq = random.choice(self.subqueues)
            subq.add(task)
        else:
            pos = self.policy.insert(task, self.tasks)
            print(f"inserted process {task.name} in {self.get_structure()} (pos {pos})")
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
        print(f"X Suspending process {self.tasks[0].name} from {self.get_structure()}")
        self.idle.append(self.tasks.pop(0))
        if self.is_empty() and (self.parent_queue != None):
            self.parent_queue.suspend()
    
    def check_preemption(self):
        if self.policy.should_preempt(self):
            self.add(self.tasks.pop(0))
            self.bursts_since_last = 0
        for q in self.subqueues:
            q.check_preemption()
    
    def is_empty(self) -> bool:
        return self.tasks == []
    
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
            return None
        self.bursts_since_last += 1
        proc : Process | None = t.burst()
        if proc != None and self.subqueues == []: # if t is a completed process (self is queue)
            self.suspend()
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
        self.active_queue : str = "" if self.process == None else self.process.parent_queue.name
        self.pqueues : List[Queue] = q.get_process_queues()
        self.tasks : Dict[str, List[Process]] = dict()
        for q in self.pqueues:
            pl = [p for p in q.tasks] # if p != self.process
            self.tasks[q.name] = pl
            
    def __str__(self):
        return f"{(self.process.name if self.process != None else '-')} " + " ".join([f"{n}: {{{' '.join([p.name for p in pl])}}}" for n, pl in self.tasks.items()])

class Frame:
    def __init__(self, t: int, qlist : List[Queue] = []):
        print(f"Creating frame {t}; remaining processes: {' '.join([p.name for p in suspended_processes])}")
        self.t = t
        self.groups : Dict[str, GroupInfo] = dict()
        self.allpt = {p.name: p.rem_time for p in processes}
        for q in qlist:
            self.load_queue(q)
        print(f"CPU: {str(self.groups['CPU'].process)} - IO: {str(self.groups['IO'].process)} - {'; '.join([f'{p.name} in {p.parent_queue}' for p in processes])}")
        print(" - ".join([q.get_structure() for q in qlist]))
        
    def load_queue(self, q: Queue):
        self.groups[q.name] = GroupInfo(q)

class GroupRenderer:
    def __init__(self, group_frames : List[GroupInfo]):
        self.queuesizes : Dict[str, int] = dict()
        self.max_process_len = 0
        for f in group_frames:
            for n, q in f.tasks.items():
                size = len(q)
                if size > self.queuesizes.get(n, -1):
                    self.queuesizes[n] = size
            if f.pt > self.max_process_len:
                self.max_process_len = f.pt
        
class GraphicsInfo:
    def __init__(self, config : dict, cpuq : Queue, ioq : Queue, frames : List[Frame]):
        self.cheight = 0
        self.maxheight = config.get("max_window_height", 800)
        self.uwidth : int = config.get("frame_width", 20)
        self.uheight : int = config.get("item_height", 20)
        self.ratio = math.sqrt(self.uwidth / self.uheight)
        self.min_q_size : int = config.get("minimum_queue_size", 1)
        self.background_c : str = config.get("background_color", "#ffffff")
        self.border_c : str = config.get("border_color", "#000000")
        self.edge_c : str = config.get("edge_color", "#000000")
        
        self.group_info : Dict[str, List[GroupInfo]] = dict()
        for f in frames:
            for gn in f.groups.keys():
                if not gn in self.group_info:
                    self.group_info[gn] = list()
                self.group_info[gn].append(f.groups[gn])
                
        print(f"Frame data: " + ' - '.join([f"{n}: [{', '.join([str(g) for g in gl])}]" for n, gl in self.group_info.items()]))
        self.groups = [GroupRenderer(i) for i in self.group_info.values()]
        print(f"Completed Group Frame Construction")
        print(" - ".join([str(g.queuesizes) for g in self.groups]))
        self.maxpt = max([g.max_process_len for g in self.groups])
        self.queuesizes = fuse_dicts([gr.queuesizes for gr in self.groups])
        self.queuepositions : Dict[str, int] = dict()
        
        self.width = self.uwidth * (4 + self.get_queue_max_size(cpuq) + self.get_queue_max_size(ioq))
        
        self.cpu_levels = self.build_levels(cpuq)
        self.io_levels = self.build_levels(ioq)
        self.core_pos : List[int] = list()
        self.calc_queue_positions([self.cpu_levels, self.io_levels])
        l = max(len(self.cpu_levels), len(self.io_levels))
        for lev in [self.cpu_levels, self.io_levels]:
            while len(lev) < l:
                lev.append(lev[-1])
        self.levels_depth = l
        self.height = min((len(frames) + self.levels_depth + 1) * self.uheight, self.maxheight)
        
        self._urdif = self.uwidth / (2 * self.maxpt)
        
        self.legendlevels : List[List[str]] = list()
    
    def get_queue_max_size(self, q : Queue):
        if q.name in self.queuesizes: return max(self.queuesizes[q.name], self.min_q_size)
        if q.subqueues:
            v = sum([self.get_queue_max_size(sq) for sq in q.subqueues])
            self.queuesizes[q.name] = v
            return v 
        raise ValueError(f"Asked queue size of unmeasured queue: {q.name}; recognized queue names are {self.queuesizes.keys()}")
        
    def qname_to_render_size(self, qn : str):
        return self.uwidth * max(self.queuesizes.get(qn, 0), self.min_q_size)
        
    def build_levels(self, rootq : Queue):
        active : Dict[Queue, int] = {rootq: self.get_queue_max_size(rootq)}
        result = [active]
        finished = False
        while not finished:
            print(f"Level building loop with active length = {active.values()}")
            na = dict()
            for q in active.keys():
                if q.subqueues != []:
                    for sq in q.subqueues:
                        na[sq] = self.get_queue_max_size(sq)
                else:
                    na[q] = self.get_queue_max_size(q)
            active = na
            result.append(active)
            
            finished = True
            for q in active.keys():
                if q.subqueues != []:
                    finished = False
        
        print(f"Resulting levels structure: {result}")
        return result
    
    def calc_queue_positions(self, levellist : List[List[Dict[Queue, int]]]):
        x = self.uwidth * 2
        for lev in levellist:
            d = lev[-1]
            for q, width in d.items():
                self.queuepositions[q.name] = x
                x += width * self.uwidth
            self.core_pos.append(x)
            x += self.uwidth
            
    def get_relative_size(self, v : float):
        return math.sqrt(v / self.maxpt)
    
    def draw_init(self, win : GraphWin):
        win.setBackground(self.background_c)
    
    def draw_legend(self, win : GraphWin):
        xd = self.width / len(processes)
        x = xd / 2
        for p in processes:
            txt = Text(Point(x, self.cheight + self.uheight / 2), p.name)
            txt.setTextColor(p.color)
            txt.draw(win)
            x += xd
        self.cheight += self.uheight
        self.draw_horizontal_rule(win)
    
    def draw_horizontal_rule(self, win : GraphWin):
        ln = Line(Point(0, self.cheight), Point(self.width, self.cheight))
        ln.setOutline(self.border_c)
        ln.draw(win)
    
    def draw_border(self, x : int, win : GraphWin, y = -1):
        if y < 0: y = self.cheight
        ln = Line(Point(x, y), Point(x, y + self.uheight))
        ln.setOutline(self.border_c)
        ln.draw(win)
    
    def draw_levels(self, win : GraphWin):
        x_base = self.uwidth * 2
        for lev in [self.cpu_levels, self.io_levels]:
            y = self.cheight
            for l in lev:
                x = x_base
                self.draw_border(x, win, y = y)
                for q, size in l.items():
                    print(f"Printing queue {q.name} with size = {size}; x = {x}, y = {y}")
                    render_size = self.uwidth * size
                    txt = Text(Point(x + render_size / 2, y + self.uheight / 2), q.name)
                    txt.setTextColor(q.color)
                    txt.draw(win)
                    x += render_size
                    self.draw_border(x, win, y = y)
                y += self.uheight
                    
            x_base += self.uwidth * sum(lev[0].values()) + self.uwidth
        self.cheight += self.levels_depth * self.uheight
        self.draw_horizontal_rule(win)
    
    def draw_frame(self, f : Frame, win : GraphWin):
        x = self.uwidth * 2
        y = self.cheight
        
        num = Text(Point(x - self.uwidth, y + self.uheight / 2), str(f.t))
        num.setTextColor(self.border_c)
        num.draw(win)
        
        core_i = 0
        for group in f.groups.values():
            if (p := group.process) != None:
                dxt = self.uwidth * group.pt / (2 * self.maxpt)
                dxb = dxt - self._urdif
                core_x = self.core_pos[core_i] + self.uwidth / 2
                pol = Polygon(Point(core_x - dxt, y), Point(core_x + dxt, y), Point(core_x + dxb, y + self.uheight), Point(core_x - dxb, y + self.uheight))
                pol.setFill(p.color)
                pol.setOutline(p.color)
                pol.draw(win)
            self.draw_border(x, win)
            for qname, pl in group.tasks.items():
                pos = self.queuepositions[qname]
                wid = self.qname_to_render_size(qname)
                self.draw_queue_processes(pos, wid, f, group, pl, win)
                if qname == group.active_queue: continue
                ln = Line(Point(pos, self.cheight), Point(pos + wid, self.cheight + self.uheight))
                ln.setOutline("#808080")
                ln.draw(win)
            x = self.core_pos[core_i] + self.uwidth
            core_i += 1
        self.cheight += self.uheight
        
    def draw_queue_processes(self, pos : int, width : int, f : Frame, g : GroupInfo, pl : List[Process], win : GraphWin):
        x = pos + width - self.uwidth / 2
        y = self.cheight + self.uheight / 2
        
        for p in pl:
            rs = f.allpt[p.name]
            dy = self.uheight * self.get_relative_size(rs) / 2
            dx = dy * self.ratio
            if p != g.process:
                fig = Rectangle(Point(x - dx, y - dy), Point(x + dx, y + dy))
            else:
                fig = Polygon(Point(x - dx, y - dy), Point(x + dx, y), Point(x - dx, y + dy))
            fig.setFill(p.color)
            fig.setOutline(self.edge_c)
            fig.draw(win)
            x -= self.uwidth
            
        self.draw_border(pos + width, win)
        
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

processes : List[Process] = list()
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
            p.completion_time = t_now
        elif t_now >= p.arrival_time:
            q = queues[p.get_queue_name()]
            q.add(p)
            to_remove.append(p)
    
    for p in to_remove:
        suspended_processes.remove(p)
    
def check_preemption():
    for q in [cpu_queue, io_queue]:
        q.check_preemption()
    
t_now : int = 0
frames : list[Frame] = list()

finished = False
while not finished:
    reallocate_suspended()
    check_preemption()
    frames.append(Frame(t_now, [cpu_queue, io_queue]))
    t_now += 1
    
    finished = suspended_processes == []
    if finished:
        for q in [cpu_queue, io_queue]:
            if not q.is_empty():
                finished = False
                break
            
    if finished or t_now > 100:
        break
    
    for q in [cpu_queue, io_queue]:
        if not q.is_empty() and (p := q.burst()):
            suspended_processes.append(p)

with open("out.txt", "w") as out:
    for p in processes:
        wait_t = p.completion_time - p.arrival_time - p.time_cost
        out.write(f"{p.name}: COST = {p.time_cost}, TIME RANGE = [{p.arrival_time}..{p.completion_time}], WAITING = {wait_t}\n")

options = config.get("options", dict())
stepbystep = options.get("step_by_step_rendering", False)

print("Finished creating frames") 
graph = GraphicsInfo(config["graphics"], cpu_queue, io_queue, frames)
print("Finished creating Graphical Info object")
win = GraphWin("Process Traceback", graph.width, graph.height, autoflush=False)
graph.draw_init(win)
print("Finished creating graphical window")

graph.draw_legend(win)
graph.draw_levels(win)
update(5)

for i in frames:
    if stepbystep:
        win.getMouse()
    graph.draw_frame(i, win)
    update(15)

try:
    while k := win.getKey():
        if k == "Down":
            for i in win.items:
                i.move(0, -5 * graph.uheight)
            update()
        elif k == "Up":
            for i in win.items:
                i.move(0, 5 * graph.uheight)
            update()
except GraphicsError:
    print("Closing window")