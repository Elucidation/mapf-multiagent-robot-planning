# TODO : WIP not functioning yet, for #9
# Polls for available tasks from DB
# Gets robot list from world sim
# Inits list of robots and their current states, available/doing task
# Assigns robots to tasks, (eventually pathfinds), completes tasks, clears robot state
# Add inventory_management_system module to path for imports (hacky)

from db_robot_task import DatabaseRobotTaskManager
from robot import Robot, RobotId
import multiagent_planner.pathfinding as pf
from typing import List, Tuple
from world_db import WorldDatabaseManager
from inventory_management_system.Item import ItemId
from inventory_management_system.TaskStatus import TaskStatus
from inventory_management_system.Order import OrderId
from inventory_management_system.Station import Task, StationId, TaskId
from warehouses.warehouse_loader import load_warehouse_yaml_xy
import time
import random


# db_name = "orders.db"
# dboi = DatabaseOrderManager(db_name)


# Checks for any tasks, completes the latest one
step_delay = [0.2, 0.8]
task_complete_delay = [0.2, 0.6]
no_task_delay = 5
no_robot_delay = 1


# radb = DatabaseRobotTaskManager()

# robot_task_allocations: list[tuple[Robot, Task]] = [()]


world_db_filename = 'world.db'  # TODO Move this to config param
wdb = WorldDatabaseManager(world_db_filename)


# Load grid positions all in x,y coordinates
WORLD_GRID, robot_home_zones, item_load_zones, station_zones = load_warehouse_yaml_xy(
    'warehouses/warehouse1.yaml')


class Job:
    "Build a job from a task, containing actual positions/paths for robot"

    def __init__(self, task: Task, robot_id: RobotId) -> None:
        self.item_zone = item_load_zones[task.item_id]
        self.station_zone = station_zones[task.station_id]
        self.robot_home = robot_home_zones[robot_id]

        self.task = task
        self.robot_id = robot_id

        self.robot_start_pos = self.get_current_robot_pos()

        self.path_robot_to_item = pf.astar(WORLD_GRID, self.robot_start_pos, self.item_zone)
        self.path_item_to_station = pf.astar(WORLD_GRID, self.item_zone, self.station_zone)
        self.path_station_to_home = pf.astar(WORLD_GRID, self.station_zone, self.robot_home)
                
        # State tracker, ladder logic
        self.started = False
        self.item_picked = False
        self.item_dropped = False
        self.robot_returned = False
        self.complete = False
    
    def get_current_robot_pos(self) -> Tuple[int, int]:
        return wdb.get_robot(self.robot_id).pos

    def __repr__(self):
        state = [self.started, self.item_picked, self.item_dropped, self.robot_returned, self.complete]
        state = [int(s) for s in state]
        return f'Job for {self.task} : {state}'

    


fake_task = Task(TaskId(0), StationId(0), OrderId(0),
                 ItemId(0), 1, TaskStatus.OPEN)


def fake_get_tasks():
    return [fake_task]


job = Job(fake_task, RobotId(0))
jobs : dict[TaskId, Job] = {}
jobs[job.task.task_id] = job

# TODO : Create jobs for tasks

# Main loop processing jobs from tasks
while True:
    tasks = fake_get_tasks()

    for task in tasks:
        job = jobs[task.task_id]
        print(job)
        if job.complete:
            continue
        if not job.started:
            print(f'Starting job for task {task}')
            wdb.set_robot_path(job.robot_id, job.path_robot_to_item)
            job.started = True
            continue
        elif not job.item_picked:
            # Check that robot is at item zone
            current_pos = job.get_current_robot_pos()
            if (current_pos != job.item_zone):
                print(f'Robot not yet to item zone {current_pos} -> {job.item_zone}')
                continue
            # TODO : Add item to held items for robot
            print(f'Item picked! Sending robot to station for task {task}')

            wdb.set_robot_path(job.robot_id, job.path_item_to_station)
            job.item_picked = True
            continue
        elif not job.item_dropped:
            # Check that robot is at station zone
            current_pos = job.get_current_robot_pos()
            if (current_pos != job.station_zone):
                print(f'Robot not yet to station zone {current_pos} -> {job.station_zone}')
                continue
            print(f'Item dropped! Sending robot back home for task {task}')
            print(f'Task {task} complete')
            
            # TODO : Drop item from held items for robot
            # TODO : Use dboi to complete task
            # dboi.add_item_to_station(task.station_id, task.item_id)
            task.status = TaskStatus.COMPLETE

            wdb.set_robot_path(job.robot_id, job.path_station_to_home)
            job.item_dropped = True
            continue
        elif not job.robot_returned:
            # Check that robot is at home zone
            current_pos = job.get_current_robot_pos()
            if (current_pos != job.robot_home):
                print(f'Robot not yet to robot home {current_pos} -> {job.robot_home}')
                continue
            print(f'Robot returned home, job complete for task {task}')
            job.robot_returned = True
            job.complete = True
            continue
    
    # Delay till next task
    delay = 5
    print(f" waiting {delay} seconds")
    time.sleep(delay)


# while True:
#     ## Check for any finished robot/tasks: make robot open, make task finished
#     allocations = radb.get_current_allocations()
#     for entry in allocations:
#         if not task:
#             continue
#         radb.check_task_state(robot.id, task)

#     # Find open task, open robot, assign robot to task

#     ## Find open task
#     # Get task (item X to station Y)
#     # tasks = dboi.get_tasks(query_status=TaskStatus.OPEN, N=1)
#     fake_task = Task(StationId(0), OrderId(0), ItemId(0), 1, TaskStatus.OPEN)
#     tasks = [fake_task]
#     if len(tasks) == 0:
#         print('No Tasks at the moment, sleeping 5 seconds')
#         time.sleep(no_task_delay)
#         continue

#     task = tasks[0]
#     print(f'Received Task {task}')

#     task.status = TaskStatus.IN_PROGRESS

#     paths = getPaths(task, robot) # [robot_to_item, item_to_station, station_to_robot_start]

#     entry = {
#         'task_id': task,
#         'robot_id': None,
#         'item_id': task.item_id,
#         'station_id': task.station_id,
#         'time_assigned': time.time(),
#         'item_picked_time': None,
#         'item_delivered_time': None,
#         'robot_finished_time': None # Once robot is back home?
#     }

#     ## Find available robot
#     robot = find_available_robot()
#     while not robot:
#         time.sleep(no_robot_delay)
#         robot = find_available_robot()

#     radb.assign_robot_to_task(task, robot)


#     ##

#     # Take 1-5 sec to complete task
#     delay = task_complete_delay[0] + random.random() * \
#         (task_complete_delay[1]-task_complete_delay[0])
#     print(f" waiting {delay} seconds")
#     time.sleep(delay)

#     # Submit task complete
#     # dboi.add_item_to_station(task.station_id, task.item_id)
#     task.status = TaskStatus.COMPLETE
#     print(f'Finished {task}')

#     # Delay till next task
#     delay = step_delay[0] + random.random() * (step_delay[1]-step_delay[0])
#     print(f" waiting {delay} seconds")
#     time.sleep(delay)
