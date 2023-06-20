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
import json
import random
from typing import Callable, Optional, Tuple
import os
import time
import redis
from inventory_management_system.Item import ItemId
from inventory_management_system.TaskKeyParser import parse_task_key_to_ids
from job import Job, JobId, JobState
import multiagent_planner.pathfinding as pf
from multiagent_planner.pathfinding import Position, Path
from multiagent_planner.pathfinding_heuristic import build_true_heuristic
from robot import Robot, RobotId, RobotStatus
from world_db import WorldDatabaseManager
from warehouse_logger import create_warehouse_logger
from warehouses.warehouse_loader import WorldInfo
# pylint: disable=redefined-outer-name

# Max number of steps to search with A*, should be ~worst case distance in grid
MAX_PATH_STEPS = int(os.getenv("MAX_PATH_STEPS", default="500"))
MAX_TIME_CHECK_JOB_SEC = float(
    os.getenv("MAX_TIME_CHECK_JOB_SEC", default="0.100"))
MAX_TIME_ASSIGN_JOB_SEC = float(
    os.getenv("MAX_TIME_ASSIGN_JOB_SEC", default="0.100"))
MAX_UPDATE_TIME_SEC = float(
    os.getenv("MAX_UPDATE_TIME_SEC", default="0.500"))


class RobotAllocator:
    """Robot Allocator, manages robots, assigning them jobs from tasks, 
    updating stations and tasks states as needed"""

    def __init__(self, logger, redis_con: redis.Redis, wdb: WorldDatabaseManager,
                 world_info: WorldInfo,
                 heuristic: Callable[[Position, Position], float]) -> None:
        self.logger = logger

        # Connect to redis database
        self.wdb = wdb

        # Tracks Order / Task, notifies item adds etc.
        self.redis_db = redis_con

        # Load grid positions all in x,y coordinates
        self.world_grid = world_info.world_grid
        self.robot_home_zones = world_info.robot_home_zones
        self.item_load_zones = world_info.item_load_zones
        self.station_zones = world_info.station_zones

        self.heuristic = heuristic
        # self.heuristic = euclidean_heuristic
        self.logger.warning(f'Heuristic used: {self.heuristic.__name__}')

        # locks for zones
        self.item_locks: dict[Position, Optional[JobId]] = {
            pos: None for pos in self.item_load_zones}
        self.station_locks: dict[Position, Optional[JobId]] = {
            pos: None for pos in self.station_zones}

        self.max_steps = MAX_PATH_STEPS  # hard-coded search tile limit for pathing

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
            robot.task_key = None
            robot.state_description = 'Waiting for task'
            if robot.pos != self.robot_home_zones[idx]:
                # Not at home, try to go home, assume current pos in any zone as not an obstacle
                dynamic_obstacles, static_obstacles = self.get_current_obstacles(
                    robot.robot_id, robot.pos, robot.pos)
                path_to_home = self.generate_path(
                    robot.pos, self.robot_home_zones[idx], dynamic_obstacles, static_obstacles)
                self.logger.warning(
                    'Starting outside of home, attempting to send home')
                robot.state_description = 'Allocator restart, trying to going home'
                if path_to_home:
                    robot.set_path(path_to_home)
        self.wdb.update_robots(self.robots)

        # Get delta time step used by world sim
        self.dt_sec = self.wdb.get_dt_sec()

        # Move all in progress tasks back to head of new
        task_keys = self.redis_db.smembers('tasks:inprogress')
        if task_keys:
            self.redis_db.lpush('tasks:new', *task_keys)
        self.redis_db.delete('tasks:inprogress')

        # Track robot allocations as allocations[robot_id] = job_id
        self.allocations: dict[RobotId, Optional[JobId]] = {
            robot.robot_id: None for robot in self.robots}

    def make_job(self, task_key: str, robot: Robot) -> Job:
        """Create a job for a given robot and task"""
        assert robot.state == RobotStatus.AVAILABLE
        
        task_ids = parse_task_key_to_ids(task_key)

        # Get positions along the route
        robot_home = self.robot_home_zones[robot.robot_id]
        item_zone = self.item_load_zones[task_ids.item_id]
        # Note: Hacky, off-by-one because indexing starts at 1, not zero
        station_zone = self.station_zones[task_ids.station_id - 1]

        # Create job and increment counter
        job_data = {
            'task_key': task_key,
            'station_id': task_ids.station_id,
            'order_id': task_ids.order_id,
            'item_id': task_ids.item_id,
            'idx': task_ids.idx,
            'robot_id': robot.robot_id,
            'robot_start_pos': robot.pos,
            'robot_home': robot_home,
            'item_zone': item_zone,
            'station_zone': station_zone,
        }
        job_id = self.job_id_counter
        self.job_id_counter = JobId(self.job_id_counter + 1)
        job = Job(job_id, job_data)
        # Set robot state
        robot.state = RobotStatus.IN_PROGRESS
        robot.state_description = 'Assigned new task'
        robot.task_key = job.task_key
        return job

    def get_current_obstacles(self, robot_id: RobotId,
                              item_zone_pos: Optional[Position] = None,
                              station_zone_pos: Optional[Position] = None,
                              ) -> tuple[set[tuple[int, int, int]], set[tuple[int, int]]]:
        """Return existing robot future paths as dynamic obstacles

        Returns a tuple of:
            set[tuple[int, int, int]]: set of (row, col, t) dynamic obstacles with current t=-1
            set[tuple[int, int]]: set of (row, col) static obstacles

        """
        # For dynamic obstacles, assume current moment is t=-1, next moment is t=0
        dynamic_obstacles: set[tuple[int, int, int]
                               ] = set()  # set{(row,col,t), ...}
        static_obstacles: set[tuple[int, int]] = set()  # set{(row,col), ...}

        this_robot = self.get_robot(robot_id)
        # Block off all other robot docks as static obstacles
        for idx, dock in enumerate(self.robot_home_zones):
            if idx == robot_id:
                continue
            static_obstacles.add((dock[0], dock[1]))

        # Block off all item zones (except any given one) as static
        for pos in self.item_load_zones:
            if pos == item_zone_pos:
                continue
            static_obstacles.add((pos[0], pos[1]))

        # Block off all station zones (except any given one) as static
        for pos in self.station_zones:
            if pos == station_zone_pos:
                continue
            static_obstacles.add((pos[0], pos[1]))

        for robot in self.robots:
            if robot.robot_id == robot_id:
                continue  # Ignore self
            if robot.pos == this_robot.pos:
                self.logger.error('Robot collision, pathing out of it')
                continue  # Ignore edge case robot collision to allow for recovering out
            # Add all positions along future path
            for t_step, pos in enumerate(robot.future_path):
                dynamic_obstacles.add((pos[0], pos[1], t_step))
                # Also add it at future and past time to keep robots from slipping nearby
                dynamic_obstacles.add((pos[0], pos[1], t_step+1))
                # TODO : This is hacky, get more precise on when robots go along paths.
                dynamic_obstacles.add((pos[0], pos[1], t_step-1))

            path_t = len(robot.future_path)
            if robot.future_path:
                # Add final position a few times to give space for robot to move
                last_pos = robot.future_path[path_t-1]
                for t_step in range(path_t, path_t+5):
                    dynamic_obstacles.add((last_pos[0], last_pos[1], t_step))
            else:
                # Robot stationary, add current robot position as static obstacle
                static_obstacles.add((robot.pos[0], robot.pos[1]))
        return (dynamic_obstacles, static_obstacles)

    def get_robot(self, robot_id: RobotId) -> Robot:
        """Get robot by id from stored list of robots"""
        # TODO : Replace this with dict[robot_id] -> robot
        for robot in self.robots:
            if robot.robot_id == robot_id:
                return robot
        raise ValueError(f'get_robot called with invalid robot id {robot_id}')

    def robot_pick_item(self, robot_id: RobotId,
                        item_id: ItemId) -> Tuple[bool, Optional[ItemId]]:
        """Robot by id pick the given item if possible, return held item."""
        # Return fail if already holding an item
        robot = self.get_robot(robot_id)
        if not robot.hold_item(item_id):
            return (False, robot.held_item_id)

        return (True, robot.held_item_id)

    def robot_drop_item(self, robot_id: RobotId) -> Tuple[bool, Optional[ItemId]]:
        """Robot by id drop held item, or false if none"""
        robot = self.get_robot(robot_id)
        item_id = robot.drop_item()
        if item_id is None:
            return (False, item_id)

        # Return success and the item dropped
        return (True, item_id)

    def get_available_robots(self) -> list[Robot]:
        """Finds all robots currently available"""
        return [robot for robot in self.robots if robot.state == RobotStatus.AVAILABLE]

    def get_first_available_robot(self) -> Optional[Robot]:
        """Get first available robot."""
        for robot in self.robots:
            if robot.state == RobotStatus.AVAILABLE:
                return robot
        return None

    def set_robot_error(self, robot_id: RobotId):
        """Set robot state to error"""
        robot = self.get_robot(robot_id)
        robot.state = RobotStatus.ERROR

    def find_and_assign_task_to_robot(self) -> Optional[Job]:
        """ Find and assign available robot an available task if they exist.
        If yes, create a job for that robot, update states and return the job. """
        robot = self.get_first_available_robot()
        if not robot:
            return None # No available robots

        # Pop task and push into inprogress
        if not self.redis_db.exists('tasks:new') or self.redis_db.llen('tasks:new') == 0:
            return None # No available tasks
        task_key = self.redis_db.lpop()
        if not task_key:
            return None
        return self.assign_task_to_robot(task_key, robot)
        
    
    def assign_task_to_robot(self, task_key: str, robot: Robot) -> Job:
        """Given available robot and task, create job and assign robot to it"""
        assert task_key is not None
        if robot.state != RobotStatus.AVAILABLE:
            raise ValueError(
                f'{robot} not available for a new job: ({repr(robot.state)} == '
                f'{repr(RobotStatus.AVAILABLE)}) = {robot.state == RobotStatus.AVAILABLE}')

        job = self.make_job(task_key, robot) # Returns task_key to tasks:new if it fails
        self.logger.info(f'Created Job: {job}')
        return job

    def update(self, robots=None, time_read=None):
        """Process jobs and assign robots tasks.
           If update takes longer than a threshold, the step is skipped and redis is not updated."""
        t_start = time.perf_counter() if time_read is None else time_read
        self.logger.debug('update start')
        
        # Update to latest robots from WDB if not passed in
        self.robots = self.wdb.get_robots() if robots is None else robots

        def update_too_long():
            """Check if time since t_start > MAX_UPDATE_TIME_SEC"""
            return (time.perf_counter() - t_start) > MAX_UPDATE_TIME_SEC
        if update_too_long():
            self.logger.warning('update started too late at %.2f ms > %.2f ms threshold, skipping',
                                (time.perf_counter() - t_start)*1000, MAX_UPDATE_TIME_SEC * 1000)
            return

        # Check and update any jobs
        job_keys = list(self.jobs)
        # TODO : Replace this with round-robin
        shuffled_job_keys = random.sample(job_keys, len(job_keys))

        # Only process jobs for up to MAX_TIME_CHECK_JOB_SEC locally and MAX_UPDATE_TIME_SEC total
        jobs_processed = 0
        processed_jobs: list[Job] = []
        for job_key in shuffled_job_keys:
            # Create a copy of the job to be changed
            job = self.jobs[job_key].copy()
            self.check_and_update_job(job)
            jobs_processed += 1
            processed_jobs.append(job)
            if ((time.perf_counter() - t_start) > MAX_TIME_CHECK_JOB_SEC) or update_too_long():
                break

        # Now check for any available robots and tasks for up to MAX_TIME_ASSIGN_JOB_SEC locally
        # and MAX_UPDATE_TIME_SEC total
        t_assign = time.perf_counter()
        new_jobs: list[Job] = []
        # Get available robots
        robots_assigned = 0
        available_robots = self.get_available_robots()
        available_robots_count = len(available_robots)
        # Get available new tasks
        new_tasks = self.redis_db.lrange('tasks:new', 0, available_robots_count)
        new_tasks_count = len(new_tasks)
        # For each available pair of robot and tasks
        for idx in range(min(available_robots_count, new_tasks_count)):
            if (time.perf_counter() - t_assign) > MAX_TIME_ASSIGN_JOB_SEC:
                break
            if update_too_long():
                break
            # Assign new task to available robot, creating a new job
            task_key = new_tasks[idx]
            robot = available_robots[idx]
            new_job = self.assign_task_to_robot(task_key, robot)
            new_jobs.append(new_job)
            robots_assigned += 1


        # Revert changes if at this point update took too long
        # Expectation: No redis writes were done up to this point.
        if update_too_long():
            update_duration_ms = (time.perf_counter() - t_start)*1000
            self.logger.error(
                f'update end, reverted due to over threshold, '
                f'took {update_duration_ms:.3f} ms > {MAX_UPDATE_TIME_SEC*1000} ms threshold, '
                f'reverting processed {jobs_processed}/{len(shuffled_job_keys)} jobs, '
                f'reverting assigned {robots_assigned}/{available_robots_count} available robots '
                f'to {new_tasks_count} available tasks')
            return

        # Batch update robots now
        self.wdb.update_robots(self.robots)
        # replace stored jobs that were processed with the chaanged ones
        for job in processed_jobs:
            # Either replace job in progress, or pop completed ones
            if job.state == JobState.COMPLETE:
                # Remove allocation and job on completion
                self.allocations[job.robot_id] = None
                self.jobs.pop(job.job_id, None)
                continue
            
            if job.state == JobState.ITEM_DROPPED:
                # Notify task complete (Order Proc adds item to station)
                self.redis_db.srem('tasks:inprogress', job.task_key)
                self.redis_db.lpush('tasks:processed', job.task_key)
                self.logger.info(f'Task {job.task_key} complete, '
                                f'Robot {job.robot_id} successfully dropped item')
            
            self.jobs[job.job_id] = job
            self.allocations[job.robot_id] = job.job_id
        
        # For newly created jobs, track them and make their tasks inprogress in redis
        for job in new_jobs:
            self.jobs[job.job_id] = job  # Track job
        # Move task keys associated with new jobs from new -> inprogress
        if new_jobs:
            task_keys = [job.task_key for job in new_jobs]
            self.redis_db.lpop('tasks:new', len(task_keys))
            self.redis_db.sadd('tasks:inprogress', *task_keys) # Set tasks in progress
        
        update_duration_ms = (time.perf_counter() - t_start)*1000
        self.logger.info(
            f'update end, took {update_duration_ms:.3f} ms, '
            f'processed {jobs_processed}/{len(shuffled_job_keys)} jobs, '
            f'assigned {robots_assigned}/{available_robots_count} available robots '
            f'to {new_tasks_count} available tasks')

    def sleep(self):
        """Sleep for dt_sec"""
        time.sleep(self.dt_sec)

    def generate_path(self, pos_a: Position, pos_b: Position,
                      dynamic_obstacles, static_obstacles) -> Path:
        """Generate a path from a to b avoiding existing robots"""
        t_start = time.perf_counter()
        stats = {
            'pos_a': pos_a,
            'pos_b': pos_b,
            'count_dynamic_obstacles': len(dynamic_obstacles),
            'count_static_obstacles': len(static_obstacles)
        }
        path = pf.st_astar(
            self.world_grid, pos_a, pos_b, dynamic_obstacles, static_obstacles=static_obstacles,
            end_fast=True, max_time=self.max_steps, heuristic=self.heuristic, stats=stats)
        self.logger.info(
            f'generate_path took {(time.perf_counter() - t_start)*1000:.3f} ms - {stats}')
        return path

    def job_start(self, job: Job) -> bool:
        """Start job, pathing robot to item zone, or home."""
        # Check if item zone lock available
        if self.item_locks[job.item_zone] and self.item_locks[job.item_zone] != job.job_id:
            # Item zone in use
            return False
        self.item_locks[job.item_zone] = job.job_id  # take lock on item zone

        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        # Try to generate new path for robot
        dynamic_obstacles, static_obstacles = self.get_current_obstacles(
            job.robot_id, item_zone_pos=job.item_zone)
        job.path_robot_to_item = self.generate_path(
            current_pos, job.item_zone, dynamic_obstacles, static_obstacles)
        if not job.path_robot_to_item:
            self.logger.warning(f'Robot {job.robot_id} no path to item zone')

            if job.robot_home == current_pos:
                return False
            # Not at home, so try going home instead for now
            path_to_home = self.generate_path(
                current_pos, job.robot_home, dynamic_obstacles, static_obstacles)
            self.logger.warning(
                f'Trying to go home {current_pos} -> {job.robot_home}')
            if path_to_home:
                robot.set_path(path_to_home)
                robot.state_description = 'Pathing home, waiting till item zone available'
            return False  # Did not start job as no path existed yet

        robot.set_path(job.path_robot_to_item)
        robot.state_description = 'Pathing to item zone'
        job.start()
        self.logger.info(f'Started {job}')
        return True

    def job_try_pick_item(self, job: Job) -> bool:
        """Have robot try and pick the item for the job."""
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
        job.pick_item()

        self.logger.info(f'Robot {job.robot_id} item picked {item_in_hand}')
        robot.state_description = f'Picked item {item_in_hand}'
        return True

    def job_go_to_station(self, job: Job) -> bool:
        """Have robot go to station."""
        # Check if station zone lock available
        if (self.station_locks[job.station_zone] and
                self.station_locks[job.station_zone] != job.job_id):
            return False  # Item zone in use
        # take lock on station zone
        self.station_locks[job.station_zone] = job.job_id

        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        # Try to generate new path for robot
        dynamic_obstacles, static_obstacles = self.get_current_obstacles(
            job.robot_id, item_zone_pos=job.item_zone, station_zone_pos=job.station_zone)
        job.path_item_to_station = self.generate_path(
            current_pos, job.station_zone, dynamic_obstacles, static_obstacles)
        if not job.path_item_to_station:
            self.logger.warning('No path to station for %s', job)
            # Try going home instead to leave space at station
            path_to_home = self.generate_path(
                current_pos, job.robot_home, dynamic_obstacles, static_obstacles)
            if path_to_home:
                robot.set_path(path_to_home)
                robot.state_description = 'Pathing home, waiting till station available'
            return False  # Did not start job as no path existed yet

        # unlock item zone since we're moving
        self.item_locks[job.item_zone] = None

        # Send robot to station
        robot.set_path(job.path_item_to_station)
        robot.state_description = 'Pathing to station'
        job.going_to_station()
        self.logger.info(
            f'Sending robot {job.robot_id} to station for task {job.task_key}')
        return True

    def job_drop_item_at_station(self, job: Job) -> bool:
        """Have robot drop item at station if possible."""
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
        if item_id != job.item_id:
            self.logger.error(
                f"Robot {job.robot_id} was holding the wrong "
                f"item: {item_id}, needed {job.item_id}")
            job.error = True
            return False

        job.drop_item()
        robot.state_description = f'Finished task: Added item {job.item_id} to station'
        return True

    def job_return_home(self, job: Job) -> bool:
        """Transition to return home state, having robot path home."""
        # Try to generate new path for robot
        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        dynamic_obstacles, static_obstacles = self.get_current_obstacles(
            job.robot_id, station_zone_pos=job.station_zone)
        job.path_station_to_home = self.generate_path(
            current_pos, job.robot_home, dynamic_obstacles, static_obstacles)
        if not job.path_station_to_home:
            self.logger.warning(f'Robot {job.robot_id} no path back home')
            return False  # Did not start job as no path existed yet
        # Send robot home
        robot.set_path(job.path_station_to_home)
        robot.state_description = 'Finished task, returning home'
        job.return_home()
        # Release lock on station
        self.station_locks[job.station_zone] = None
        self.logger.info(
            f'Sending Robot {job.robot_id} back home for {job.task_key}')
        return True

    def job_arrive_home(self, job: Job) -> bool:
        """If robot at home, finish the job."""
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
        return self.job_complete(job)

    def job_complete(self, job: Job) -> bool:
        """Complete job and make robot available"""
        # Normally this will be called in line with arriving home.
        job.complete()
        # Make robot available
        robot = self.get_robot(job.robot_id)
        robot.state = RobotStatus.AVAILABLE
        robot.task_key = None
        robot.state_description = 'Waiting for task'
        # Expect update to remove allocations and completed jobs separately
        return True

    def job_restart(self, job: Job):
        """If something went wrong, reset job state to start, same robot/task"""
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
        dynamic_obstacles, static_obstacles = self.get_current_obstacles(
            job.robot_id)
        path_to_home = self.generate_path(
            current_pos, job.robot_home, dynamic_obstacles, static_obstacles)
        if path_to_home:
            robot.set_path(path_to_home)
        # Set robots start pos to where it is currently
        # job.robot_start_pos = robot.pos
        return False

    # Map states to methods
    state_methods = {
        JobState.WAITING_TO_START: 'job_start',
        JobState.PICKING_ITEM: 'job_try_pick_item',
        JobState.ITEM_PICKED: 'job_go_to_station',
        JobState.GOING_TO_STATION: 'job_drop_item_at_station',
        JobState.ITEM_DROPPED: 'job_return_home',
        JobState.RETURNING_HOME: 'job_arrive_home',
        JobState.COMPLETE: None,
        JobState.ERROR: 'job_restart',
    }

    def check_and_update_job(self, job: Job) -> bool:
        """Process a job based on the current state. """

        # Get the method for the current state
        method_name = self.state_methods.get(job.state)
        # print(f'check update for {job.state} : {method_name}')
        if method_name is None:
            return False
        method = getattr(self, method_name)

        if method is None:
            return False

        return method(job)

    def step(self):
        """Main update step for robot allocator, runs after world update."""
        # Wait for world state update
        response = self.redis_db.xread(
            {'world:state': '$'}, block=1000, count=1)
        time_read = time.perf_counter()
        if not response:
            return
        #  Parse robot data from update message
        timestamp, data = response[0][1][0]
        world_sim_t = int(data['t'])
        robots = [Robot.from_json(json_data)
                  for json_data in json.loads(data['robots'])]

        self.logger.info(
            'Step start T=%d timestamp=%s ---------------------------------'
            '--------------------------------------------------------', world_sim_t, timestamp)
        self.update(robots, time_read=time_read)
        self.logger.debug('Step end')


def wait_for_redis_connection(redis_con):
    """Wait until a redis ping succeeds, try every 2 seconds."""
    while True:
        try:
            if redis_con.ping():
                break
            else:
                logger.warning(
                    'Ping failed for redis server %s:%d, waiting', REDIS_HOST, REDIS_PORT)
        except redis.ConnectionError:
            logger.error(
                'Redis unable to connect %s:%d, waiting', REDIS_HOST, REDIS_PORT)
        time.sleep(2)


if __name__ == '__main__':
    logger = create_warehouse_logger('robot_allocator')

    # Load world info from yaml
    world_info = WorldInfo.from_yaml(
        os.getenv('WAREHOUSE_YAML', 'warehouses/main_warehouse.yaml'))

    # Build true heuristic function
    t_start = time.perf_counter()
    logger.info('Building true heuristic')
    # Build true heuristic grid
    true_heuristic_dict = build_true_heuristic(world_info.world_grid, world_info.get_all_zones())
    logger.info('Built true heuristic grid in %.2f ms',
                (time.perf_counter() - t_start)*1000)

    def true_heuristic(pos_a: Position, pos_b: Position) -> float:
        """Returns A* shortest path between any two points based on world_grid"""
        return true_heuristic_dict[pos_b][pos_a]

    # Set up redis
    REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))
    redis_con = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    wait_for_redis_connection(redis_con)

    # Init Robot Allocator
    wdb = WorldDatabaseManager(redis_con)  # Contains World/Robot info
    robot_mgr = RobotAllocator(
        logger, redis_con, wdb, world_info, true_heuristic)

    # Main loop processing jobs from tasks
    logger.info('Robot Allocator started, waiting for world:state updates')
    while True:
        try:
            robot_mgr.step()
        except redis.exceptions.ConnectionError as e:
            logger.warning('Redis connection error, waiting and trying again.')
            time.sleep(1)
        except redis.exceptions.TimeoutError as e:
            logger.warning('Redis time-out error, waiting and trying again.')
            time.sleep(1)
