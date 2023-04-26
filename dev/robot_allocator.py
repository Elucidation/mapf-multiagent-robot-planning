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
from typing import Optional, Tuple, NewType
import logging
import time
import signal
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
import zmq

# Allow Ctrl-C to break while zmq socket.recv is going
signal.signal(signal.SIGINT, signal.SIG_DFL)

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
        self.robot_id = robot.robot_id

        # Stops on route
        self.robot_start_pos = robot.pos
        self.item_zone = item_load_zone
        self.station_zone = station_zone
        self.robot_home = robot_home_zone

        # Paths
        self.path_robot_to_item: Path
        self.path_item_to_station: Path
        self.path_station_to_home: Path

        self.reset()

    def reset(self):
        # Paths
        self.path_robot_to_item = []
        self.path_item_to_station = []
        self.path_station_to_home = []

        # State tracker, ladder logic
        self.started = False
        self.item_picked = False
        self.going_to_station = False
        self.item_dropped = False
        self.returning_home = False
        self.robot_returned = False
        self.complete = False
        self.error = False

    def __repr__(self):
        state = [self.started, self.item_picked, self.going_to_station,
                 self.item_dropped, self.returning_home,
                 self.robot_returned, self.complete, self.error]
        state_str = ""
        if self.error:
            state_str = "ERROR"
        elif self.complete:
            state_str = "COMPLETE"
        elif self.robot_returned:
            state_str = "RETURNED"
        elif self.returning_home:
            state_str = "GOING HOME"
        elif self.item_dropped:
            state_str = "ITEM DROPPED"
        elif self.going_to_station:
            state_str = "GOING TO STATION"
        elif self.item_picked:
            state_str = "ITEM PICKED"
        elif self.started:
            state_str = "STARTED"
        else:
            state_str = "OPEN"

        state = [int(s) for s in state]
        return (f'Job [Robot {self.robot_id},Task {self.task.task_id},Order {self.task.order_id}]'
                f' Move {self.task.item_id} to {self.task.station_id}: Progress {state_str}, '
                f'P {len(self.path_robot_to_item)} {len(self.path_item_to_station)} '
                f'{len(self.path_station_to_home)}')


class RobotAllocator:
    """Robot Allocator, manages robots, assigning them jobs from tasks, 
    updating stations and tasks states as needed"""

    def __init__(self, logger=logging) -> None:
        self.logger = logger
        # Connect to databases
        self.wdb = WorldDatabaseManager(
            WORLD_DB_PATH)  # Contains World/Robot info
        self.ims_db = DatabaseOrderManager(
            MAIN_DB)  # Contains Task information

        # Load grid positions all in x,y coordinates
        (self.world_grid, self.robot_home_zones,
         self.item_load_zones, self.station_zones) = load_warehouse_yaml_xy(
            'warehouses/warehouse3.yaml')

        # Keep track of all jobs, even completed
        self.job_id_counter: JobId = JobId(0)
        self.jobs: dict[JobId, Job] = {}

        # Get all robots regardless of state
        # assume no robots will be added or removed for duration of this instance
        self.robots = self.wdb.get_robots()
        # Reset Robot states and drop any held items
        for robot in self.robots:
            robot.held_item_id = None
            robot.state = RobotStatus.AVAILABLE
        self.wdb.update_robots(self.robots)
        self.wdb.con.commit()

        # Get delta time step used by world sim
        self.dt_sec = self.wdb.get_dt_sec()

        # Reset Task in progress states
        tasks = self.ims_db.get_tasks(query_status=TaskStatus.IN_PROGRESS)
        for task in tasks:
            self.ims_db.update_task_status(task.task_id, TaskStatus.OPEN)
        self.ims_db.commit()

        # Track robot allocations as allocations[robot_id] = Job
        self.allocations: dict[RobotId, Optional[Job]] = {
            robot.robot_id: None for robot in self.robots}

    def make_job(self, task: Task, robot: Robot) -> Optional[Job]:
        """Try to generate and return job if pathing is possible, None otherwise"""
        if robot.state != RobotStatus.AVAILABLE:
            raise ValueError(
                f'{robot} not available for a new job: ({repr(robot.state)} == '
                f'{repr(RobotStatus.AVAILABLE)}) = {robot.state == RobotStatus.AVAILABLE}')
        if task.status != TaskStatus.OPEN:
            raise ValueError(f'{task} not open for a new job')
        # Get positions along the route
        robot_home = self.robot_home_zones[robot.robot_id]
        item_zone = self.item_load_zones[task.item_id]
        # Note: Hacky, off-by-one because sqlite3 db starts indexing at 1, not zero
        station_zone = self.station_zones[task.station_id - 1]

        # Create job
        job_id = self.job_id_counter  # TODO : This will move to DB auto increment
        # Job success
        self.job_id_counter = JobId(self.job_id_counter + 1)
        job = Job(job_id, robot_home, item_zone, station_zone, task, robot)
        self.jobs[job_id] = job  # Track job
        assert robot.robot_id == job.robot_id
        self.allocations[robot.robot_id] = job  # Track robot allocation
        # Set task state
        self.ims_db.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
        task.status = TaskStatus.IN_PROGRESS  # Update local task instance as well
        # Set robot state
        robot.state = RobotStatus.IN_PROGRESS
        # TODO : Update robot?
        return job

    def get_current_dynamic_obstacles(self, max_t: int = 20) -> set[tuple[int, int, int]]:
        """Return existing robot future paths as dynamic obstacles

        Returns:
            set[tuple[int, int, int]]: set of (row, col, t) dynamic obstacles with current t=-1
        """
        # For dynamic obstacles, assume current moment is t=-1, next moment is t=0
        dynamic_obstacles: set[tuple[int, int, int]
                               ] = set()  # set{(row,col,t), ...}
        for robot in self.robots:
            # Add all positions along future path
            for t, pos in enumerate(robot.future_path):
                dynamic_obstacles.add((pos[0], pos[1], t))
                # Also add it at future and past time to keep robots from slipping nearby
                dynamic_obstacles.add((pos[0], pos[1], t+1))
                # TODO : This is hacky, get more precise on when robots go along paths.
                dynamic_obstacles.add((pos[0], pos[1], t-1))

            path_t = len(robot.future_path)
            if robot.future_path:
                # Add final position a few times to give space for robot to move
                last_pos = robot.future_path[path_t-1]
                # dynamic_obstacles.add((last_pos[0], last_pos[1], path_t))
                # dynamic_obstacles.add((last_pos[0], last_pos[1], path_t + 1))
                # dynamic_obstacles.add((last_pos[0], last_pos[1], path_t + 2))
                for t in range(path_t, path_t+5):
                    dynamic_obstacles.add((last_pos[0], last_pos[1], t))

            else:
                # Robot stationary, add current robot position up to limit
                for t in range(max_t):
                    dynamic_obstacles.add((robot.pos[0], robot.pos[1], t))
        return dynamic_obstacles

    def get_robot(self, robot_id: RobotId) -> Robot:
        # TODO : Replace this with dict[robot_id] -> robot
        for robot in self.robots:
            if robot.robot_id == robot_id:
                return robot
        raise ValueError(f'get_robot called with invalid robot id {robot_id}')

    def robot_pick_item(self, robot_id: RobotId,
                        item_id: ItemId) -> Tuple[bool, Optional[ItemId]]:
        # Return fail if already holding an item
        robot = self.get_robot(robot_id)
        if not robot.hold_item(item_id):
            return (False, robot.held_item_id)

        # Update the robot in the DB
        # TODO : Update robot?
        return (True, robot.held_item_id)

    def robot_drop_item(self, robot_id: RobotId) -> Tuple[bool, Optional[ItemId]]:
        # Return fail if it wasn't holding an item
        robot = self.get_robot(robot_id)
        item_id = robot.drop_item()
        if item_id is None:
            return (False, item_id)

        # Update the robot in the DB
        # TODO : Update robot?
        # Return success and the item dropped
        return (True, item_id)

    def get_available_robots(self) -> list[Robot]:
        # Finds all robots currently available
        return [robot for robot in self.robots if robot.state == RobotStatus.AVAILABLE]

    def set_robot_error(self, robot_id: RobotId):
        robot = self.get_robot(robot_id)
        robot.state = RobotStatus.ERROR
        # TODO : Update robot?

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
            self.logger.info(f'ASSIGNED TASK TO ROBOT: {robot} : {job}')
        else:
            self.logger.debug('Could not create job this turn')
        return job

    def update(self):
        t_start = time.perf_counter()
        logger.debug('update start')
        # Update to latest robots from WDB
        self.robots = self.wdb.get_robots()

        # Check and update any jobs
        for job in self.jobs.values():
            self.check_and_update_job(job)

        # Now check for any available robots and tasks
        self.assign_task_to_robot()

        # Commit transactions to IMS DB
        self.ims_db.commit()
        # Batch update robots now
        self.wdb.update_robots(self.robots)
        self.wdb.con.commit()
        logger.debug(
            f'update end, took {(time.perf_counter() - t_start)*1000:.3f} ms')

    def sleep(self):
        time.sleep(self.dt_sec)

    def generate_path(self, pos_a: Position, pos_b: Position, max_steps: int = 40) -> Path:
        """Generate a path from a to b avoiding existing robots"""
        t_start = time.perf_counter()
        dynamic_obstacles = self.get_current_dynamic_obstacles(max_steps)
        path = pf.st_astar(
            self.world_grid, pos_a, pos_b, dynamic_obstacles, end_fast=True, max_time=max_steps)
        logger.debug(
            f'generate_path took {(time.perf_counter() - t_start)*1000:.3f} ms : {pos_a} -> {pos_b} max_steps={max_steps} : {path}')
        return path

    def job_start(self, job: Job) -> bool:
        # TODO : Check if item zone lock available
        # take lock on item zone
        # else: don't start yet (go home)
        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        # Try to generate new path for robot
        job.path_robot_to_item = self.generate_path(current_pos, job.item_zone)
        if not job.path_robot_to_item:
            self.logger.warning(f'Robot {job.robot_id} no path to item zone')

            if job.robot_home == current_pos:
                return False
            # Not at home, so try going home instead for now
            path_to_home = self.generate_path(current_pos, job.robot_home)
            self.logger.warning(
                f'Going home? {job.robot_home} - {current_pos} = {path_to_home}')
            if path_to_home:
                robot.set_path(path_to_home)
            return False  # Did not start job as no path existed yet

        self.logger.info(f'Starting job {job} for Robot {job.robot_id}')
        robot.set_path(job.path_robot_to_item)
        job.started = True
        return True

    def job_try_pick_item(self, job: Job) -> bool:
        # Check that robot is at item zone or has a path
        robot = self.get_robot(job.robot_id)
        if robot.pos != job.item_zone:
            if not robot.future_path:
                self.logger.error('Robot path diverged from job, reset state')
                job.started = False
                return False
            self.logger.debug(
                f'Robot {job.robot_id} not yet to item zone {robot.pos} -> {job.item_zone}')
            return False

        # Add item to held items for robot
        success, item_in_hand = self.robot_pick_item(
            job.robot_id, job.task.item_id)
        if not success:
            self.logger.error(
                f'Robot {job.robot_id} could not pick item for '
                f'job {job}, already holding {item_in_hand}')
            job.error = True
            return False
        job.item_picked = True

        self.logger.info(f'Robot {job.robot_id} item picked {item_in_hand}')
        return True

    def job_go_to_station(self, job: Job) -> bool:
        # TODO : Check if station zone lock available
        # take lock on station zone
        # else: don't start yet (go home)
        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        # Try to generate new path for robot
        job.path_item_to_station = self.generate_path(
            current_pos, job.station_zone)
        if not job.path_item_to_station:
            logger.warning(f'No path to station for {job}')
            # Try going home instead to leave space at station
            path_to_home = self.generate_path(
                current_pos, job.robot_home)
            if path_to_home:
                robot.set_path(path_to_home)
            return False  # Did not start job as no path existed yet

        # TODO : unlock item zone since we're moving
        # TODO : consider a step in-between to go to a waiting zone for items to stations

        # Send robot to station
        robot.set_path(job.path_item_to_station)
        job.going_to_station = True
        self.logger.info(
            f'Sending robot {job.robot_id} to station for task {job.task}')
        return True

    def job_drop_item_at_station(self, job: Job) -> bool:
        # Check that robot is at station zone
        robot = self.get_robot(job.robot_id)
        if robot.pos != job.station_zone:
            if not robot.future_path:
                self.logger.error('Robot path diverged from job, reset state')
                job.going_to_station = False
                return False
            self.logger.debug(
                f'Robot {job.robot_id} not yet to station zone {robot.pos} -> {job.station_zone}')
            return False

        # Add Item to station (this finishes the task too)
        # TODO : Drop item from held items for robot
        drop_success, item_id = self.robot_drop_item(job.robot_id)
        if not drop_success:
            self.logger.error(
                f"Robot {job.robot_id} didn't have item to drop: {job.robot_id} held {item_id}")
            self.set_robot_error(job.robot_id)
            job.error = True
            return False
        elif item_id != job.task.item_id:
            self.logger.error(
                f"Robot {job.robot_id} was holding the wrong "
                f"item: {item_id}, needed {job.task.item_id}")
            job.error = True
            return False

        # TODO : Validate item added successfully
        
        self.ims_db.add_item_to_station_fast(job.task.station_id, job.task.quantity, job.task.task_id)
        # This only modifies the task instance in the job
        job.task.quantity -= 1
        job.task.status = TaskStatus.COMPLETE
        self.logger.info(f'Task {job.task} complete, '
                         f'Robot {job.robot_id} successfully dropped item')

        job.item_dropped = True
        return True

    def job_return_home(self, job: Job) -> bool:
        # Try to generate new path for robot
        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        job.path_station_to_home = self.generate_path(
            current_pos, job.robot_home)
        if not job.path_station_to_home:
            self.logger.warning(f'Robot {job.robot_id} no path back home')
            return False  # Did not start job as no path existed yet
        # Send robot home
        robot.set_path(job.path_station_to_home)
        job.returning_home = True
        self.logger.info(
            f'Sending Robot {job.robot_id} back home for '
            f'task {job.task}: {job.path_station_to_home}')
        return True

    def job_arrive_home(self, job: Job) -> bool:
        # Check that robot is at home zone
        robot = self.get_robot(job.robot_id)
        if robot.pos != job.robot_home:
            if not robot.future_path:
                self.logger.error('Robot path diverged from job, reset state')
                job.returning_home = False
                return False
            self.logger.debug(
                f'Robot {job.robot_id} not yet to robot home {robot.pos} -> {job.robot_home}')
            return False
        self.logger.info(
            f'Robot {job.robot_id} returned home, job complete for task {job.task}')
        job.robot_returned = True
        job.complete = True

        # Make robot available
        robot = self.get_robot(job.robot_id)
        robot.state = RobotStatus.AVAILABLE
        # TODO : Update robot 

        # Remove job from allocations
        self.allocations[job.robot_id] = None
        return True

    def job_restart(self, job):
        self.logger.error(
            f'{job} in error for, resetting job and Robot {job.robot_id} etc.')

        # Make robot available and drop any held items
        robot = self.get_robot(job.robot_id)
        robot.state = RobotStatus.AVAILABLE
        robot.held_item_id = None
        # TODO : Update robot 

        # Reset the job
        job.reset()
        # Try going home instead to leave space at station
        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        path_to_home = self.generate_path(current_pos, job.robot_home)
        if path_to_home:
            robot.set_path(path_to_home)
        # Set robots start pos to where it is currently
        # job.robot_start_pos = robot.pos
        return False

    def check_and_update_job(self, job: Job) -> bool:
        # Go through state ladder for a job
        # TODO : Send event logs to DB for metrics later.
        if job.complete:
            return False
        if job.error:
            return self.job_restart(job)

        if not job.started:
            return self.job_start(job)
        elif not job.item_picked:
            return self.job_try_pick_item(job)
        elif not job.going_to_station:
            return self.job_go_to_station(job)
        elif not job.item_dropped:
            return self.job_drop_item_at_station(job)
        elif not job.returning_home:
            return self.job_return_home(job)
        elif not job.robot_returned:
            return self.job_arrive_home(job)
        return False


def create_logger():
    logging.basicConfig(filename='robot_allocator.log', encoding='utf-8', filemode='w',
                        level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger_ra = logging.getLogger('robot_allocator')
    logger_ra.setLevel(logging.DEBUG)
    stream_logger = logging.StreamHandler()
    stream_logger.setLevel(logging.INFO)
    logger_ra.addHandler(stream_logger)
    return logger_ra


if __name__ == '__main__':
    logger = create_logger()

    # 0MQ Socket to subscribe to world sim state updates
    PORT = "50523"
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{PORT}")

    robot_mgr = RobotAllocator(logger=logger)

    # Subscribe to world 0mq updates
    socket.setsockopt_string(zmq.SUBSCRIBE, "WORLD")

    # Main loop processing jobs from tasks
    logger.info('Robot Allocator running')

    while True:
        logger.debug('Waiting for 0mq world update')
        string = socket.recv()
        topic, messagedata = string.split()
        world_sim_t = int(messagedata)
        logger.info(
            f'Step start T={world_sim_t} -----------------------------------------------------------------------------------------------')
        robot_mgr.update()

        if any(robot_mgr.allocations.values()):
            # logger.debug('- Current available tasks: '
            #              f'{[task.task_id for task in robot_mgr.get_available_tasks()]}')
            logger.debug('- Current job allocations')
            for allocated_robot_id, allocated_job in robot_mgr.allocations.items():
                logger.debug(
                    f'RobotId {allocated_robot_id} : {allocated_job}')
            logger.debug(
                f'- Robots: {robot_mgr.robots}')
            logger.debug('---')

        # Delay till next task
        logger.debug('Step end')
        # robot_mgr.sleep()
