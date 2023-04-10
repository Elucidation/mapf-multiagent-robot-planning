"""Contains Robot Allocator and Job classes

Robot Allocator:
 - Poll Inventory Management System DB for available tasks
 - Poll World DB for available robots and general world position info
 - Assign available Robots to Task as a Job
 - Track current jobs, their states:
    - Generate and assign paths for Robots based on the job state
    - Move along state of jobs as robots complete paths
    - Pick/Drop items for robots from item zones to station zones
    - Update stations by filling items as they happen
"""
# TODO : WIP not functioning yet, for #9
# Polls for available tasks from DB
# Gets robot list from world sim
# Inits list of robots and their current states, available/doing task
# Assigns robots to tasks, (eventually pathfinds), completes tasks, clears robot state
# Add inventory_management_system module to path for imports (hacky)

from typing import Optional, Tuple, NewType
import time
# import random
import multiagent_planner.pathfinding as pf
from robot import Robot, RobotId, RobotStatus
# from db_robot_task import DatabaseRobotTaskManager
from world_db import WorldDatabaseManager, WORLD_DB_PATH
from inventory_management_system.Item import ItemId
from inventory_management_system.TaskStatus import TaskStatus
from inventory_management_system.Order import OrderId
from inventory_management_system.Station import Task, StationId, TaskId
from inventory_management_system.database_order_manager import DatabaseOrderManager, MAIN_DB
from warehouses.warehouse_loader import load_warehouse_yaml_xy, Position


# Checks for any tasks, completes the latest one
step_delay = [0.2, 0.8]
task_complete_delay = [0.2, 0.6]
no_task_delay = 5
no_robot_delay = 1


# radb = DatabaseRobotTaskManager()

# robot_task_allocations: list[tuple[Robot, Task]] = [()]

JobId = NewType('JobId', int)


class Job:
    "Build a job from a task, containing actual positions/paths for robot"

    def __init__(self, job_id: JobId, grid, robot_home_zones: list[Position],
                 item_load_zones: list[Position],
                 station_zones: list[Position], task: Task, robot: Robot) -> None:
        self.job_id = job_id
        self.task = task
        self.robot_id = robot.id

        # Get positions along the route
        self.robot_home = robot_home_zones[robot.id]
        self.item_zone = item_load_zones[task.item_id]
        # Note: Hacky, off-by-one because sqlite3 db starts indexing at 1, not zero
        self.station_zone = station_zones[task.station_id - 1]

        self.robot_start_pos = robot.pos

        # Generate paths with astar
        self.path_robot_to_item = pf.astar(
            grid, self.robot_start_pos, self.item_zone)
        self.path_item_to_station = pf.astar(
            grid, self.item_zone, self.station_zone)
        self.path_station_to_home = pf.astar(
            grid, self.station_zone, self.robot_home)

        # State tracker, ladder logic
        self.started = False
        self.item_picked = False
        self.item_dropped = False
        self.robot_returned = False
        self.complete = False

    def get_current_robot_pos(self, world_dbm: WorldDatabaseManager) -> Tuple[int, int]:
        return world_dbm.get_robot(self.robot_id).pos

    def __repr__(self):
        state = [self.started, self.item_picked,
                 self.item_dropped, self.robot_returned, self.complete]
        state = [int(s) for s in state]
        return f'Job for <{self.task}>: Progress {state}'


class RobotAllocator:
    """Robot Allocator, manages robots, assigning them jobs from tasks, updating stations and tasks states as needed"""

    def __init__(self) -> None:
        # Connect to databases
        self.wdb = WorldDatabaseManager(
            WORLD_DB_PATH)  # Contains World/Robot info
        self.ims_db = DatabaseOrderManager(
            MAIN_DB)  # Contains Task information

        # Load grid positions all in x,y coordinates
        self.world_grid, self.robot_home_zones, self.item_load_zones, self.station_zones = load_warehouse_yaml_xy(
            'warehouses/warehouse2.yaml')

        # Keep track of all jobs, even completed
        self.job_id_counter: JobId = JobId(0)
        self.jobs: dict[JobId, Job] = {}

        # Get all robots regardless of state, assume no robots will be added or removed for duration of this instance
        robots = self.wdb.get_robots()
        # Reset Robot states
        for robot in robots:
            robot.state = RobotStatus.AVAILABLE
        self.wdb.update_robots(robots)

        # Track robot allocations as allocations[robot_id] = Job
        self.allocations: dict[RobotId, Optional[Job]] = {
            robot.id: None for robot in robots}

    def make_job(self, task: Task, robot: Robot):
        if robot.state != RobotStatus.AVAILABLE:
            raise ValueError(
                f'{robot} not available for a new job: ({repr(robot.state)} == {repr(RobotStatus.AVAILABLE)}) = {robot.state == RobotStatus.AVAILABLE}')
        if task.status != TaskStatus.OPEN:
            raise ValueError(f'{task} not open for a new job')

        # TODO : This will move to DB auto increment
        job_id = self.job_id_counter
        self.job_id_counter = JobId(self.job_id_counter + 1)

        # Create job
        job = Job(job_id, self.world_grid, self.robot_home_zones,
                  self.item_load_zones, self.station_zones, task, robot)
        self.jobs[job_id] = job  # Track job
        self.allocations[robot.id] = job  # Track robot allocation
        # Set task state
        self.ims_db.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
        task.status = TaskStatus.IN_PROGRESS  # Update local task instance as well
        # Set robot state
        robot.state = RobotStatus.IN_PROGRESS
        self.wdb.update_robots([robot])

        return job

    def get_robot(self, robot_id: RobotId):
        return self.wdb.get_robot(robot_id)

    def get_available_robots(self) -> list[Robot]:
        # Finds all robots currently available
        return self.wdb.get_robots(query_state=str(RobotStatus.AVAILABLE))

    def get_available_tasks(self, limit_rows: int = 5) -> list[Task]:
        return self.ims_db.get_tasks(TaskStatus.OPEN, limit_rows)

    def assign_task_to_robot(self) -> Optional[Job]:
        # Check if any available robots and available tasks
        # If yes, create a job for that robot, update states and return the job here
        available_robots = self.get_available_robots()
        if not available_robots:
            return None

        available_tasks = self.get_available_tasks()
        if not available_tasks:
            return None

        # Available robots and tasks, create a job for the first pair
        robot = available_robots[0]
        task = available_tasks[0]
        job = self.make_job(task, robot)
        print(
            f'**ASSIGNED TASK TO ROBOT found pair: {robot} - {task} : {job}**')
        return job

    def update(self):
        # Check and update any jobs
        for job in robot_mgr.jobs.values():
            self.check_and_update_job(job)

        # Now check for any available robots and tasks
        robot_mgr.assign_task_to_robot()

    def check_and_update_job(self, job: Job):
        # TODO : Split this up into functions
        if job.complete:
            return
        if not job.started:
            print(f'Starting job {job}')
            robot_mgr.wdb.set_robot_path(job.robot_id, job.path_robot_to_item)
            job.started = True
            return
        elif not job.item_picked:
            # Check that robot is at item zone
            current_pos = job.get_current_robot_pos(robot_mgr.wdb)
            if (current_pos != job.item_zone):
                print(
                    f'Robot not yet to item zone {current_pos} -> {job.item_zone}')
                return
            # TODO : Add item to held items for robot
            print(f'Item picked! Sending robot to station for task {job.task}')

            robot_mgr.wdb.set_robot_path(
                job.robot_id, job.path_item_to_station)
            job.item_picked = True
            return
        elif not job.item_dropped:
            # Check that robot is at station zone
            current_pos = job.get_current_robot_pos(robot_mgr.wdb)
            if (current_pos != job.station_zone):
                print(
                    f'Robot not yet to station zone {current_pos} -> {job.station_zone}')
                return

            # Add Item to station (this finishes the task too)
            # TODO : Drop item from held items for robot
            # TODO : Validate item added successfully
            self.ims_db.add_item_to_station(job.task.station_id, job.task.item_id)
            # This only modifies the task instance in the job
            job.task.status = TaskStatus.COMPLETE
            print(f'Item dropped! Sending robot back home for task {job.task}')
            print(f'Task {job.task} complete')

            robot_mgr.wdb.set_robot_path(
                job.robot_id, job.path_station_to_home)
            job.item_dropped = True
            return
        elif not job.robot_returned:
            # Check that robot is at home zone
            current_pos = job.get_current_robot_pos(robot_mgr.wdb)
            if (current_pos != job.robot_home):
                print(
                    f'Robot not yet to robot home {current_pos} -> {job.robot_home}')
                return
            print(f'Robot returned home, job complete for task {job.task}')
            job.robot_returned = True
            job.complete = True

            # Make robot available
            robot = self.get_robot(job.robot_id)
            robot.state = RobotStatus.AVAILABLE
            self.wdb.update_robots([robot])

            return


robot_mgr = RobotAllocator()

# Main loop processing jobs from tasks
while True:
    print('-------')
    robot_mgr.update()

    # Delay till next task
    delay = 1
    print(f" waiting {delay} seconds")
    print('---')
    print('- Current available tasks:')
    for task in robot_mgr.get_available_tasks():
        print(task)
    print('- Current job allocations')
    for robot_id, job in robot_mgr.allocations.items():
        print(f'RobotId {robot_id} : {job}')
    print('- Robots:')
    print(robot_mgr.get_available_robots())
    print('---')
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
