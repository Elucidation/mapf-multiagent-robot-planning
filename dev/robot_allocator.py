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
import logging
import time
# import random
import multiagent_planner.pathfinding as pf
from multiagent_planner.pathfinding import Position, Path
from robot import Robot, RobotId, RobotStatus
# from db_robot_task import DatabaseRobotTaskManager
from world_db import WorldDatabaseManager, WORLD_DB_PATH
from inventory_management_system.Item import ItemId
from inventory_management_system.TaskStatus import TaskStatus
from inventory_management_system.Station import Task
from inventory_management_system.database_order_manager import DatabaseOrderManager, MAIN_DB
from warehouses.warehouse_loader import load_warehouse_yaml_xy

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("robot_allocator")
# logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
# log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

# radb = DatabaseRobotTaskManager()

# robot_task_allocations: list[tuple[Robot, Task]] = [()]

JobId = NewType('JobId', int)


class Job:
    "Build a job from a task, containing actual positions/paths for robot"

    def __init__(self, job_id: JobId, robot_home_zone: Position, item_load_zone: Position,
                 station_zone: Position, task: Task, robot: Robot) -> None:
        # Job-related metadata
        self.job_id = job_id
        self.task = task
        self.robot_id = robot.id

        # Stops on route
        self.robot_start_pos = robot.pos
        self.item_zone = item_load_zone
        self.station_zone = station_zone
        self.robot_home = robot_home_zone

        # Paths
        self.path_robot_to_item: Path = []
        self.path_item_to_station: Path = []
        self.path_station_to_home: Path = []

        # State tracker, ladder logic
        self.started = False
        self.item_picked = False
        self.item_dropped = False
        self.returning_home = False
        self.robot_returned = False
        self.complete = False

    def get_current_robot_pos(self, world_dbm: WorldDatabaseManager) -> Tuple[int, int]:
        return world_dbm.get_robot(self.robot_id).pos

    def __repr__(self):
        state = [self.started, self.item_picked,
                 self.item_dropped, self.returning_home, self.robot_returned, self.complete]
        state = [int(s) for s in state]
        return (f'Job [Robot {self.robot_id},Task {self.task.task_id},Order {self.task.order_id}]'
                f' Move {self.task.item_id} to {self.task.station_id}: Progress {state}')


class RobotAllocator:
    """Robot Allocator, manages robots, assigning them jobs from tasks, 
    updating stations and tasks states as needed"""

    def __init__(self) -> None:
        # Connect to databases
        self.wdb = WorldDatabaseManager(
            WORLD_DB_PATH)  # Contains World/Robot info
        self.ims_db = DatabaseOrderManager(
            MAIN_DB)  # Contains Task information

        # Load grid positions all in x,y coordinates
        (self.world_grid, self.robot_home_zones,
         self.item_load_zones, self.station_zones) = load_warehouse_yaml_xy(
            'warehouses/warehouse2.yaml')

        # Keep track of all jobs, even completed
        self.job_id_counter: JobId = JobId(0)
        self.jobs: dict[JobId, Job] = {}

        # Get all robots regardless of state
        # assume no robots will be added or removed for duration of this instance
        robots = self.wdb.get_robots()
        # Reset Robot states and drop any held items
        for robot in robots:
            robot.held_item_id = None
            robot.state = RobotStatus.AVAILABLE
        self.wdb.update_robots(robots)

        # Reset Task in progress states
        tasks = self.ims_db.get_tasks(query_status=TaskStatus.IN_PROGRESS)
        for task in tasks:
            self.ims_db.update_task_status(task.task_id, TaskStatus.OPEN)

        # Track robot allocations as allocations[robot_id] = Job
        self.allocations: dict[RobotId, Optional[Job]] = {
            robot.id: None for robot in robots}

    def make_job(self, task: Task, robot: Robot) -> Optional[Job]:
        """Try to generate and return job if pathing is possible, None otherwise"""
        if robot.state != RobotStatus.AVAILABLE:
            raise ValueError(
                f'{robot} not available for a new job: ({repr(robot.state)} == '
                f'{repr(RobotStatus.AVAILABLE)}) = {robot.state == RobotStatus.AVAILABLE}')
        if task.status != TaskStatus.OPEN:
            raise ValueError(f'{task} not open for a new job')
        # Get positions along the route
        robot_home = self.robot_home_zones[robot.id]
        item_zone = self.item_load_zones[task.item_id]
        # Note: Hacky, off-by-one because sqlite3 db starts indexing at 1, not zero
        station_zone = self.station_zones[task.station_id - 1]

        # Create job
        job_id = self.job_id_counter  # TODO : This will move to DB auto increment
        # Job success
        self.job_id_counter = JobId(self.job_id_counter + 1)
        job = Job(job_id, robot_home, item_zone, station_zone, task, robot)
        self.jobs[job_id] = job  # Track job
        self.allocations[robot.id] = job  # Track robot allocation
        # Set task state
        self.ims_db.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
        task.status = TaskStatus.IN_PROGRESS  # Update local task instance as well
        # Set robot state
        robot.state = RobotStatus.IN_PROGRESS
        self.wdb.update_robots([robot])
        return job

    def get_current_dynamic_obstacles(self, max_t:int = 20) -> set[tuple[int, int, int]]:
        """Return existing robot future paths as dynamic obstacles

        Returns:
            set[tuple[int, int, int]]: set of (row, col, t) dynamic obstacles with current t=-1
        """        
        # For dynamic obstacles, assume current moment is t=-1, next moment is t=0
        robots = self.wdb.get_robots()  # Get current future paths for all other robots
        dynamic_obstacles: set[tuple[int, int, int]
                               ] = set()  # set{(row,col,t), ...}
        for robot in robots:
            # Add all positions along future path
            for t, pos in enumerate(robot.future_path):
                dynamic_obstacles.add((pos[0], pos[1], t))
                dynamic_obstacles.add((pos[0], pos[1], t+1)) # Also add it at future time

            path_t = len(robot.future_path)
            if robot.future_path:
                # Add final position a few times to give space for robot to move
                last_pos = robot.future_path[path_t-1]
                dynamic_obstacles.add((last_pos[0], last_pos[1], path_t))
                dynamic_obstacles.add((last_pos[0], last_pos[1], path_t + 1))
                    
            else:
                # Robot stationary, add current robot position up to limit
                for t in range(max_t):
                    dynamic_obstacles.add((robot.pos[0], robot.pos[1], t))
        return dynamic_obstacles

    def get_robot(self, robot_id: RobotId):
        return self.wdb.get_robot(robot_id)

    def robot_pick_item(self, robot_id: RobotId,
                        item_id: ItemId) -> Tuple[bool, Optional[ItemId]]:
        # Return fail if already holding an item
        robot = self.wdb.get_robot(robot_id)
        if not robot.hold_item(item_id):
            return (False, robot.held_item_id)

        # Update the robot in the DB
        self.wdb.update_robots([robot])
        return (True, robot.held_item_id)

    def robot_drop_item(self, robot_id: RobotId) -> Tuple[bool, Optional[ItemId]]:
        # Return fail if it wasn't holding an item
        robot = self.wdb.get_robot(robot_id)
        item_id = robot.drop_item()
        if item_id is None:
            return (False, item_id)

        # Update the robot in the DB
        self.wdb.update_robots([robot])
        # Return success and the item dropped
        return (True, item_id)

    def get_available_robots(self) -> list[Robot]:
        # Finds all robots currently available
        return self.wdb.get_robots(query_state=str(RobotStatus.AVAILABLE))

    def set_robot_error(self, robot_id: RobotId):
        robot = self.wdb.get_robot(robot_id)
        robot.state = RobotStatus.ERROR
        self.wdb.update_robots([robot])

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
        if job:
            logging.info(f'ASSIGNED TASK TO ROBOT: {robot} : {job}')
        else:
            logging.debug('Could not create job this turn')
        return job

    def update(self):
        # Check and update any jobs
        for job in robot_mgr.jobs.values():
            self.check_and_update_job(job)

        # Now check for any available robots and tasks
        robot_mgr.assign_task_to_robot()

    def generate_path(self, pos_a: Position, pos_b: Position) -> Path:
        """Generate a path from a to b avoiding existing robots"""
        dynamic_obstacles = self.get_current_dynamic_obstacles()
        return pf.st_astar(
            self.world_grid, pos_a, pos_b, dynamic_obstacles, end_fast=True)

    def job_start(self, job: Job) -> bool:
        # Try to generate new path for robot
        job.path_robot_to_item = self.generate_path(job.robot_start_pos, job.item_zone)
        if not job.path_robot_to_item:
            return False  # Did not start job as no path existed yet

        logging.info(f'Starting job {job}')
        robot_mgr.wdb.set_robot_path(job.robot_id, job.path_robot_to_item)
        job.started = True
        return True

    def job_try_pick_item(self, job: Job) -> bool:
        # Check that robot is at item zone
        current_pos = job.get_current_robot_pos(robot_mgr.wdb)
        if current_pos != job.item_zone:
            logging.debug(
                f'Robot not yet to item zone {current_pos} -> {job.item_zone}')
            return False

        # Add item to held items for robot
        success, item_in_hand = self.robot_pick_item(job.robot_id, job.task.item_id)
        if not success:
            logging.error(f'Robot could not pick item for job {job}, already holding {item_in_hand}')
        job.item_picked = True

        logging.info(
            f'Item picked! Sending robot to station for task {job.task}')
        return True

    def job_go_to_station(self, job: Job) -> bool:
        # Try to generate new path for robot
        job.path_item_to_station = self.generate_path(job.item_zone, job.station_zone)
        if not job.path_item_to_station:
            return False  # Did not start job as no path existed yet
        
        # Send robot to station
        robot_mgr.wdb.set_robot_path(
            job.robot_id, job.path_item_to_station)
        return True

    def job_drop_item_at_station(self, job: Job) -> bool:
        # Check that robot is at station zone
        current_pos = job.get_current_robot_pos(robot_mgr.wdb)
        if current_pos != job.station_zone:
            logging.debug(
                f'Robot not yet to station zone {current_pos} -> {job.station_zone}')
            return False

        # Add Item to station (this finishes the task too)
        # TODO : Drop item from held items for robot
        drop_success, item_id = self.robot_drop_item(job.robot_id)
        if not drop_success:
            logging.error(
                f"Robot didn't have item to drop: {job.robot_id} held {item_id}")
            self.set_robot_error(job.robot_id)
            return False
        elif item_id != job.task.item_id:
            logging.error(
                f"Robot was holding wrong item: {item_id}, needed {job.task.item_id}")
            return False

        # TODO : Validate item added successfully
        self.ims_db.add_item_to_station(
            job.task.station_id, job.task.item_id)
        # This only modifies the task instance in the job
        job.task.status = TaskStatus.COMPLETE
        logging.info(
            f'Item dropped! Sending robot back home for task {job.task}')
        logging.info(f'Task {job.task} complete')

        job.item_dropped = True
        return True

    def job_return_home(self, job: Job) -> bool:
        # Try to generate new path for robot
        job.path_station_to_home = self.generate_path(job.station_zone, job.robot_home)
        if not job.path_station_to_home:
            return False  # Did not start job as no path existed yet
        # Send robot home
        robot_mgr.wdb.set_robot_path(
            job.robot_id, job.path_station_to_home)
        job.returning_home = True
        return True

    def job_arrive_home(self, job: Job) -> bool:
        # Check that robot is at home zone
        current_pos = job.get_current_robot_pos(robot_mgr.wdb)
        if current_pos != job.robot_home:
            logging.debug(
                f'Robot not yet to robot home {current_pos} -> {job.robot_home}')
            return False
        logging.info(f'Robot returned home, job complete for task {job.task}')
        job.robot_returned = True
        job.complete = True

        # Make robot available
        robot = self.get_robot(job.robot_id)
        robot.state = RobotStatus.AVAILABLE
        self.wdb.update_robots([robot])
        return True

    def check_and_update_job(self, job: Job) -> bool:
        # Go through state ladder for a job
        # TODO : Send event logs to DB for metrics later.
        if job.complete:
            return False
        if not job.started:
            return self.job_start(job)
        elif not job.item_picked:
            if not self.job_try_pick_item(job):
                return False
            return self.job_go_to_station(job)
        elif not job.item_dropped:
            return self.job_drop_item_at_station(job)
        elif not job.returning_home:
            return self.job_return_home(job)
        elif not job.robot_returned:
            return self.job_arrive_home(job)
        return False


if __name__ == '__main__':
    robot_mgr = RobotAllocator()

    # Main loop processing jobs from tasks
    DELAY_SEC = 0.2
    logger.info('Robot Allocator running')
    while True:
        logging.debug('-------')
        robot_mgr.update()

        # Delay till next task
        if any(robot_mgr.allocations.values()):
            logging.debug(f" waiting {DELAY_SEC} seconds")
            logging.debug('---')
            logging.debug(f'- Current available tasks: {[task.task_id for task in robot_mgr.get_available_tasks()]}')
            logging.debug('- Current job allocations')
            for allocated_robot_id, allocated_job in robot_mgr.allocations.items():
                logging.debug(f'RobotId {allocated_robot_id} : {allocated_job}')
            logging.debug(f'- Available Robots: {robot_mgr.get_available_robots()}')
            logging.debug('---')
        time.sleep(DELAY_SEC)
