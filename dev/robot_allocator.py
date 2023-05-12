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
import os
import time
import sqlite3
from inventory_management_system.Order import OrderId
from inventory_management_system.Station import StationId
from inventory_management_system.Item import ItemId
from inventory_management_system.TaskStatus import TaskStatus
import multiagent_planner.pathfinding as pf
from multiagent_planner.pathfinding import Position, Path
from robot import Robot, RobotId, RobotStatus
from world_db import WorldDatabaseManager
from warehouse_logger import create_warehouse_logger
from warehouses.warehouse_loader import load_warehouse_yaml_xy
import redis
# pylint: disable=redefined-outer-name

JobId = NewType('JobId', int)


class Job:
    "Build a job from a task, containing actual positions/paths for robot"

    def __init__(self, job_id: JobId, job_data: dict) -> None:
        # Job-related metadata
        self.job_id = job_id
        self.task_key: str = job_data['task']['task_key']
        self.station_id: StationId = job_data['task']['station_id']
        self.order_id: OrderId = job_data['task']['order_id']
        self.item_id: ItemId = job_data['task']['item_id']
        self.idx: int = job_data['task']['idx']

        self.robot_id: RobotId = job_data['robot']['robot'].robot_id

        # Stops on route
        self.robot_start_pos: Position = job_data['robot']['robot'].pos
        self.item_zone: Position = job_data['robot']['item_zone']
        self.station_zone: Position = job_data['robot']['station_zone']
        self.robot_home: Position = job_data['robot']['robot_home']

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
        return (f'Job [Robot {self.robot_id}, Task {self.task_key}: Progress {state_str}, '
                f'P {len(self.path_robot_to_item)} {len(self.path_item_to_station)} '
                f'{len(self.path_station_to_home)}')


class RobotAllocator:
    """Robot Allocator, manages robots, assigning them jobs from tasks, 
    updating stations and tasks states as needed"""

    def __init__(self, logger=logging, redis_con: redis.Redis = None) -> None:
        self.logger = logger

        # Connect to redis database
        self.wdb = WorldDatabaseManager(redis_con)  # Contains World/Robot info

        # Tracks Order / Task, notifies item adds etc.
        self.redis_db = redis_con  # Optional

        # Load grid positions all in x,y coordinates
        (self.world_grid, self.robot_home_zones,
         self.item_load_zones, self.station_zones) = load_warehouse_yaml_xy(
            'warehouses/warehouse3.yaml')

        # locks for zones
        self.item_locks: dict[Position, Optional[JobId]] = {
            pos: None for pos in self.item_load_zones}
        self.station_locks: dict[Position, Optional[JobId]] = {
            pos: None for pos in self.station_zones}

        self.max_steps = 40  # hard-coded search tile limit for pathing

        # Keep track of all jobs, even completed
        self.job_id_counter: JobId = JobId(0)
        self.jobs: dict[JobId, Job] = {}

        # Get all robots regardless of state
        # assume no robots will be added or removed for duration of this instance
        self.robots = self.wdb.get_robots()
        # Reset Robot states and drop any held items
        for idx, robot in enumerate(self.robots):
            robot.held_item_id = None
            robot.state = RobotStatus.AVAILABLE
            if robot.pos != self.robot_home_zones[idx]:
                # Not at home, try to go home, assume current pos in any zone as not an obstacle
                dynamic_obstacles = self.get_current_dynamic_obstacles(
                    robot.robot_id, robot.pos, robot.pos)
                path_to_home = self.generate_path(
                    robot.pos, self.robot_home_zones[idx], dynamic_obstacles)
                self.logger.warning(
                    f'Starting outside of home, attempting to send home: {path_to_home}')
                if path_to_home:
                    robot.set_path(path_to_home)
        self.wdb.update_robots(self.robots)

        # Get delta time step used by world sim
        self.dt_sec = self.wdb.get_dt_sec()

        # Move all in progress tasks back to head of new
        task_keys = self.redis_db.smembers('tasks:inprogress')
        if (task_keys):
            self.redis_db.lpush('tasks:new', *task_keys)
        self.redis_db.delete('tasks:inprogress')

        # Track robot allocations as allocations[robot_id] = Job
        self.allocations: dict[RobotId, Optional[Job]] = {
            robot.robot_id: None for robot in self.robots}

    def make_job(self, task_key: str, robot: Robot) -> Optional[Job]:
        """Try to generate and return job if pathing is possible, None otherwise"""
        if robot.state != RobotStatus.AVAILABLE:
            # Return task to new queue
            task_key = self.redis_db.lpush('tasks:new', task_key)
            raise ValueError(
                f'{robot} not available for a new job: ({repr(robot.state)} == '
                f'{repr(RobotStatus.AVAILABLE)}) = {robot.state == RobotStatus.AVAILABLE}')

        # TODO : pull this out
        # Task key contains it all 'task:station:<id>:order:<id>:<item_id>:<idx>'
        _, _, station_id, _, order_id, item_id, idx = task_key.split(':')
        station_id = StationId(int(station_id))
        order_id = OrderId(int(order_id))
        item_id = ItemId(int(item_id))
        idx = int(idx)

        # Get positions along the route
        robot_home = self.robot_home_zones[robot.robot_id]
        item_zone = self.item_load_zones[item_id]
        # Note: Hacky, off-by-one because sqlite3 db starts indexing at 1, not zero
        station_zone = self.station_zones[station_id - 1]

        # Create job and increment counter
        job_data = {
            'task': {
                'task_key': task_key,
                'station_id': station_id,
                'order_id': order_id,
                'item_id': item_id,
                'idx': idx,
            },
            'robot': {
                'robot': robot,
                'robot_home': robot_home,
                'item_zone': item_zone,
                'station_zone': station_zone,
            }
        }
        job_id = self.job_id_counter
        self.job_id_counter = JobId(self.job_id_counter + 1)
        job = Job(job_id, job_data)
        self.jobs[job_id] = job  # Track job
        assert robot.robot_id == job.robot_id
        self.allocations[robot.robot_id] = job  # Track robot allocation
        # Set task in progress
        self.redis_db.sadd('tasks:inprogress', task_key)
        # Set robot state
        robot.state = RobotStatus.IN_PROGRESS
        robot.state_description = 'Assigned new task'
        robot.task_key = job.task_key
        return job

    def get_current_dynamic_obstacles(self, robot_id: RobotId,
                                      item_zone_pos: Optional[Position] = None,
                                      station_zone_pos: Optional[Position] = None,
                                      ) -> set[tuple[int, int, int]]:
        """Return existing robot future paths as dynamic obstacles

        Returns:
            set[tuple[int, int, int]]: set of (row, col, t) dynamic obstacles with current t=-1
        """
        # For dynamic obstacles, assume current moment is t=-1, next moment is t=0
        dynamic_obstacles: set[tuple[int, int, int]
                               ] = set()  # set{(row,col,t), ...}

        # TODO : Consider creating static obstacles instead of time-bound ones
        # Block off all other robot docks as dynamic obstacles
        for idx, dock in enumerate(self.robot_home_zones):
            if idx == robot_id:
                continue
            for t in range(self.max_steps):
                dynamic_obstacles.add((dock[0], dock[1], t))

        # Block off all item zones (except any given one)
        for pos in self.item_load_zones:
            if pos == item_zone_pos:
                continue
            for t in range(self.max_steps):
                dynamic_obstacles.add((pos[0], pos[1], t))

        # Block off all station zones (except any given one)
        for pos in self.station_zones:
            if pos == station_zone_pos:
                continue
            for t in range(self.max_steps):
                dynamic_obstacles.add((pos[0], pos[1], t))

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
                for t in range(path_t, path_t+5):
                    dynamic_obstacles.add((last_pos[0], last_pos[1], t))

            else:
                # Robot stationary, add current robot position up to limit
                for t in range(self.max_steps):
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

        return (True, robot.held_item_id)

    def robot_drop_item(self, robot_id: RobotId) -> Tuple[bool, Optional[ItemId]]:
        # Return fail if it wasn't holding an item
        robot = self.get_robot(robot_id)
        item_id = robot.drop_item()
        if item_id is None:
            return (False, item_id)

        # Return success and the item dropped
        return (True, item_id)

    def get_available_robots(self) -> list[Robot]:
        # Finds all robots currently available
        return [robot for robot in self.robots if robot.state == RobotStatus.AVAILABLE]

    def set_robot_error(self, robot_id: RobotId):
        robot = self.get_robot(robot_id)
        robot.state = RobotStatus.ERROR

    def assign_task_to_robot(self) -> Optional[Job]:
        # Check if any available robots and available tasks
        # If yes, create a job for that robot, update states and return the job here
        try:
            available_robots = self.get_available_robots()
            if not available_robots:
                return None

            # Pop task and push into inprogress
            task_key = self.redis_db.lpop('tasks:new')
            if not task_key:
                return None
        except sqlite3.Error as err:
            logger.error(
                f'Couldn\'t access DB, did not assign anything: {err}')
            return None

        # Available robots and tasks, create a job for the first pair
        robot = available_robots[0]
        job = self.make_job(task_key, robot)
        if job:
            self.logger.info(f'ASSIGNED TASK TO ROBOT: {robot} : {job}')
        else:
            self.logger.debug(
                'Could not create job this turn, returning task to new')
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

        # Batch update robots now
        self.wdb.update_robots(self.robots)
        update_duration_ms = (time.perf_counter() - t_start)*1000
        logger.debug(
            f'update end, took {update_duration_ms:.3f} ms')

    def sleep(self):
        time.sleep(self.dt_sec)

    def generate_path(self, pos_a: Position, pos_b: Position, dynamic_obstacles) -> Path:
        """Generate a path from a to b avoiding existing robots"""
        t_start = time.perf_counter()
        path = pf.st_astar(
            self.world_grid, pos_a, pos_b, dynamic_obstacles,
            end_fast=True, max_time=self.max_steps)
        logger.debug(
            f'generate_path took {(time.perf_counter() - t_start)*1000:.3f} ms')
        return path

    def job_start(self, job: Job) -> bool:
        # Check if item zone lock available
        if self.item_locks[job.item_zone] and self.item_locks[job.item_zone] != job.job_id:
            # Item zone in use
            return False
        self.item_locks[job.item_zone] = job.job_id  # take lock on item zone

        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        # Try to generate new path for robot
        dynamic_obstacles = self.get_current_dynamic_obstacles(
            job.robot_id, item_zone_pos=job.item_zone)
        job.path_robot_to_item = self.generate_path(
            current_pos, job.item_zone, dynamic_obstacles)
        if not job.path_robot_to_item:
            self.logger.warning(f'Robot {job.robot_id} no path to item zone')

            if job.robot_home == current_pos:
                return False
            # Not at home, so try going home instead for now
            path_to_home = self.generate_path(
                current_pos, job.robot_home, dynamic_obstacles)
            self.logger.warning(
                f'Going home? {job.robot_home} - {current_pos} = {path_to_home}')
            if path_to_home:
                robot.set_path(path_to_home)
                robot.state_description = 'Pathing home, waiting till item zone available'
            return False  # Did not start job as no path existed yet

        self.logger.info(f'Starting job {job} for Robot {job.robot_id}')
        robot.set_path(job.path_robot_to_item)
        robot.state_description = 'Pathing to item zone'
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
            job.robot_id, job.item_id)
        if not success:
            self.logger.error(
                f'Robot {job.robot_id} could not pick item for '
                f'job {job}, already holding {item_in_hand}')
            job.error = True
            return False
        job.item_picked = True

        self.logger.info(f'Robot {job.robot_id} item picked {item_in_hand}')
        robot.state_description = f'Picked item {item_in_hand}'
        return True

    def job_go_to_station(self, job: Job) -> bool:
        # Check if station zone lock available
        if (self.station_locks[job.station_zone] and
                self.station_locks[job.station_zone] != job.job_id):
            return False  # Item zone in use
        # take lock on station zone
        self.station_locks[job.station_zone] = job.job_id

        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        # Try to generate new path for robot
        dynamic_obstacles = self.get_current_dynamic_obstacles(
            job.robot_id, item_zone_pos=job.item_zone, station_zone_pos=job.station_zone)
        job.path_item_to_station = self.generate_path(
            current_pos, job.station_zone, dynamic_obstacles)
        if not job.path_item_to_station:
            logger.warning(f'No path to station for {job}')
            # Try going home instead to leave space at station
            path_to_home = self.generate_path(
                current_pos, job.robot_home, dynamic_obstacles)
            if path_to_home:
                robot.set_path(path_to_home)
                robot.state_description = 'Pathing home, waiting till station available'
            return False  # Did not start job as no path existed yet

        # unlock item zone since we're moving
        self.item_locks[job.item_zone] = None

        # Send robot to station
        robot.set_path(job.path_item_to_station)
        robot.state_description = 'Pathing to station'
        job.going_to_station = True
        self.logger.info(
            f'Sending robot {job.robot_id} to station for task {job.task_key}')
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
        # Drop item from held items for robot
        drop_success, item_id = self.robot_drop_item(job.robot_id)
        if not drop_success:
            self.logger.error(
                f"Robot {job.robot_id} didn't have item to drop: {job.robot_id} held {item_id}")
            self.set_robot_error(job.robot_id)
            job.error = True
            return False
        elif item_id != job.item_id:
            self.logger.error(
                f"Robot {job.robot_id} was holding the wrong "
                f"item: {item_id}, needed {job.item_id}")
            job.error = True
            return False

        # Notify task complete (Order Proc adds item to station)
        redis_con.srem('tasks:inprogress', job.task_key)
        redis_con.lpush('tasks:processed', job.task_key)
        # This only modifies the task instance in the job
        job.status = TaskStatus.COMPLETE
        self.logger.info(f'Task {job.task_key} complete, '
                         f'Robot {job.robot_id} successfully dropped item')

        job.item_dropped = True
        robot.state_description = f'Finished task: Added item {job.item_id} to station'
        return True

    def job_return_home(self, job: Job) -> bool:
        # Try to generate new path for robot
        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        dynamic_obstacles = self.get_current_dynamic_obstacles(
            job.robot_id, station_zone_pos=job.station_zone)
        job.path_station_to_home = self.generate_path(
            current_pos, job.robot_home, dynamic_obstacles)
        if not job.path_station_to_home:
            self.logger.warning(f'Robot {job.robot_id} no path back home')
            return False  # Did not start job as no path existed yet
        # Send robot home
        robot.set_path(job.path_station_to_home)
        robot.state_description = 'Finished task, returning home'
        job.returning_home = True
        # Release lock on station
        self.station_locks[job.station_zone] = None
        self.logger.info(
            f'Sending Robot {job.robot_id} back home for {job.task_key}')
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
            f'Robot {job.robot_id} returned home, job complete for task {job.task_key}')
        job.robot_returned = True
        job.complete = True

        # Make robot available
        robot = self.get_robot(job.robot_id)
        robot.state = RobotStatus.AVAILABLE
        robot.state_description = 'Waiting for task'
        # Remove job from allocations
        self.allocations[job.robot_id] = None
        return True

    def job_restart(self, job: Job):
        self.logger.error(
            f'{job} in error for, resetting job and Robot {job.robot_id} etc.')

        # Make robot available and drop any held items
        robot = self.get_robot(job.robot_id)
        robot.state = RobotStatus.AVAILABLE
        robot.held_item_id = None

        # Reset the job
        job.reset()
        # Clear any locks it may have had
        if robot.pos in self.item_locks and self.item_locks[robot.pos] == job.job_id:
            self.item_locks[robot.pos] = None
        if robot.pos in self.station_locks and self.station_locks[robot.pos] == job.job_id:
            self.station_locks[robot.pos] = None

        # Try going home instead to leave space at station
        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        dynamic_obstacles = self.get_current_dynamic_obstacles(job.robot_id)
        path_to_home = self.generate_path(
            current_pos, job.robot_home, dynamic_obstacles)
        if path_to_home:
            robot.set_path(path_to_home)
        # Set robots start pos to where it is currently
        # job.robot_start_pos = robot.pos
        return False

    def check_and_update_job(self, job: Job) -> bool:
        # Go through state ladder for a job
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


if __name__ == '__main__':
    logger = create_warehouse_logger('robot_allocator')

    # Set up redis
    REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))
    redis_con = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_sub = redis_con.pubsub()
    redis_sub.subscribe('WORLD_T')
    logger.info('Redis Subscribed to WORLD_T updates')

    # Init Robot Allocator (may wait for databases to exist)
    robot_mgr = RobotAllocator(logger=logger, redis_con=redis_con)

    # Main loop processing jobs from tasks
    logger.info('Robot Allocator started')
    for world_t_message in redis_sub.listen():
        world_sim_t = int(world_t_message['data'])
        logger.info(
            f'Step start T={world_sim_t} ---------------------------------------'
            '--------------------------------------------------------')
        robot_mgr.update()

        if any(robot_mgr.allocations.values()):
            logger.debug('- Current job allocations')
            for allocated_robot_id, allocated_job in robot_mgr.allocations.items():
                logger.debug(
                    f'RobotId {allocated_robot_id} : {allocated_job}')

        # Delay till next task
        logger.debug('Step end')
