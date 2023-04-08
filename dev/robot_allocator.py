# TODO : WIP not functioning yet, for #9
# Polls for available tasks from DB
# Gets robot list from world sim
# Inits list of robots and their current states, available/doing task
# Assigns robots to tasks, (eventually pathfinds), completes tasks, clears robot state


# from database_order_manager import DatabaseOrderManager
import time
import random

# Add inventory_management_system module to path for imports (hacky)
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR,"inventory_management_system"))

# from TaskStatus import TaskStatus
from Station import Task, StationId
from Order import OrderId
from TaskStatus import TaskStatus
from Item import ItemId
from world_db import WorldDatabaseManager

# db_name = "orders.db"
# dboi = DatabaseOrderManager(db_name)

from robot import Robot, RobotId

from db_robot_task import DatabaseRobotTaskManager

# Checks for any tasks, completes the latest one
step_delay = [0.2, 0.8]
task_complete_delay = [0.2, 0.6]
no_task_delay = 5
no_robot_delay = 1

def get_world_robots():
    return [Robot(RobotId(0), (0, 0))]

robots = get_world_robots()

# radb = DatabaseRobotTaskManager()

def find_available_robot():
    # todo, check robot assigned table
    return robots[0]

# robot_task_allocations: list[tuple[Robot, Task]] = [()]


world_db_filename = 'world.db' # TODO Move this to config param
wdb = WorldDatabaseManager(world_db_filename)

# #8 fixed path robot 1 home zone -> item 1 zone -> station 1 zone
fixed_path_1 = [(1,1),(1,2),(1,3),
                (2,3),(2,2),(3,2),(4,2),(4,1),(5,1),(6,1),(6,2),(6,3),
                (6,4),(6,5),(7,5),(8,5),(8,4),(8,3),(8,2),(9,2),(10,2),
                (10,3),(10,4),(10,5),(10,6),(10,7),
                (11,7)]
# paths are in x,y
wdb.set_robot_path(RobotId(0), fixed_path_1)

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
