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
from typing import Optional, Tuple
import os
import time
import redis
from inventory_management_system.Item import ItemId
from inventory_management_system.TaskKeyParser import parse_task_key_to_ids
from job import Job, JobId, JobState
import multiagent_planner.pathfinding as pf
from multiagent_planner.pathfinding import Position, Path
from multiagent_planner.pathfinding_heuristic import load_heuristic
from robot import Robot, RobotId, RobotStatus
from world_db import WorldDatabaseManager
from warehouse_logger import create_warehouse_logger
from warehouses.warehouse_loader import WorldInfo
# pylint: disable=redefined-outer-name

# Max number of steps to search with A*, should be ~worst case distance in grid
MAX_PATH_STEPS = int(os.getenv("MAX_PATH_STEPS", default="500"))
# How much time robot allocator should leave before end of its update and world sim next step
SAFETY_FACTOR_SEC = float(
    os.getenv("SAFETY_FACTOR_SEC", default="0.200"))

class RobotAllocator:
    """Robot Allocator, manages robots, assigning them jobs from tasks, 
    updating stations and tasks states as needed"""

    def __init__(self, logger, redis_con: redis.Redis, wdb: WorldDatabaseManager,
                 world_info: WorldInfo,
                 heuristic_dict: dict[Position, 'np.ndarray']) -> None:
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

        self.heuristic_dict = heuristic_dict

        # locks for zones
        self.item_locks: dict[Position, Optional[JobId]] = {
            pos: None for pos in self.item_load_zones}
        self.station_locks: dict[Position, Optional[JobId]] = {
            pos: None for pos in self.station_zones}

        self.max_steps = MAX_PATH_STEPS  # hard-coded search tile limit for pathing

        # Keep track of all jobs, even completed
        self.job_id_counter: JobId = JobId(0)
        self.jobs: dict[JobId, Job] = {}

        # Get delta time step used by world sim
        self.dt_sec = self.wdb.get_dt_sec()
        self.world_sim_t = None

        # Using world info set up static dynamic obstacles
        self.static_obstacles = self.get_all_static_obstacles()

        # Try and wait for world state update to get data and reset robots
        response = self.redis_db.xread(
            {'world:state': '$'}, block=1000, count=1)
        if response:
            #  Parse robot data from update message
            timestamp, data = response[0][1][0]
            self.world_sim_t = int(data['t'])
            self.robots = [Robot.from_json(json_data)
                           for json_data in json.loads(data['robots'])]
            self.logger.info(
                'RA restart Step start T=%d timestamp=%s %s',
                self.world_sim_t, timestamp, '-'*100)
        else:
            # Get all robots regardless of state
            # assume no robots will be added or removed for duration of this instance
            self.robots = self.wdb.get_robots()

        # Track robot allocations as allocations[robot_id] = job_id
        self.allocations: dict[RobotId, Optional[JobId]] = {
            robot.robot_id: None for robot in self.robots}

        # Latest dynamic obstacles, reset on update(), updated with every new path in that cycle
        self.latest_dynamic_obstacles = None

        # Try to find paths for robots to go home, since robots no longer are pathing, no
        # issue with this taking more than one time step.
        for idx, robot in enumerate(self.robots):
            # On RA reset we assume any existing tasks/jobs are lost for the robot,
            # so drop item and task, assign it a job to go home if it's not already there.
            robot.held_item_id = None
            robot.task_key = None
            if robot.pos == self.robot_home_zones[idx]:
                robot.set_path([])  # Clear any paths
                robot.state_description = 'Waiting for task'
                robot.state = RobotStatus.AVAILABLE
                continue

            # Assign a job to go home if it's not already there.
            job = self.make_and_assign_taskless_return_home_job(robot)
            self.logger.warning(
                f'{robot.robot_id} starting outside of home, assigning taskless job home {job}')
            self.jobs[job.job_id] = job
            self.allocations[robot.robot_id] = job.job_id
        self.wdb.update_robots(self.robots)  # Update new robot state

        # Move all in progress tasks back to head of new
        task_keys = self.redis_db.smembers('tasks:inprogress')
        pipeline = self.redis_db.pipeline()
        if task_keys:
            pipeline.lpush('tasks:new', *task_keys)
        pipeline.delete('tasks:inprogress')
        pipeline.execute()

    def get_all_static_obstacles(self):
        """Get all static obstacles"""
        static_obstacles: set[tuple[int, int]] = set()  # set{(row,col), ...}
        # Maeke all zones static obstacles (lifted later for individual robots)
        static_obstacles.update(self.robot_home_zones)
        static_obstacles.update(self.item_load_zones)
        static_obstacles.update(self.station_zones)
        return static_obstacles

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

    def make_and_assign_taskless_return_home_job(self, robot: Robot) -> Job:
        """Create and assign a taskless job for a given robot to go home."""
        robot_home = self.robot_home_zones[robot.robot_id]

        # Create job and increment counter
        job_data = {
            'task_key': '',
            'station_id': None,
            'order_id': None,
            'item_id': None,
            'idx': None,
            'robot_id': robot.robot_id,
            'robot_start_pos': robot.pos,
            'robot_home': robot_home,
            'item_zone': None,
            'station_zone': None,
        }
        job_id = self.job_id_counter
        self.job_id_counter = JobId(self.job_id_counter + 1)
        job = Job(job_id, job_data)
        job.state = JobState.RESTART_MGR_GO_HOME  # Next stop is returning home
        # Set robot state
        robot.state = RobotStatus.IN_PROGRESS
        robot.state_description = 'Allocator restart, trying to return home'
        robot.task_key = None
        # Set current pos or end pos locks if they end in zones
        if robot.pos in self.station_locks:
            self.station_locks[robot.pos] = job_id
        elif robot.pos in self.item_locks:
            self.item_locks[robot.pos] = job_id
        if robot.future_path:
            end_pos = robot.future_path[-1]
            if end_pos in self.station_locks:
                self.station_locks[end_pos] = job_id
            elif end_pos in self.item_locks:
                self.item_locks[end_pos] = job_id
        return job

    def get_all_current_dynamic_obstacles(self) -> set[tuple[int, int, int]]:
        """Return existing robot future paths as dynamic obstacles

        Returns:
            set[tuple[int, int, int]]: set of (row, col, t) dynamic obstacles with current t=-1

        """
        # For dynamic obstacles, assume current moment is t=-1, next moment is t=0
        dynamic_obstacles: set[tuple[int, int, int]
                               ] = set()  # set{(row,col,t), ...}

        for robot in self.robots:
            self.add_path_as_obstacle(dynamic_obstacles, robot.future_path)

        return dynamic_obstacles

    def add_path_as_obstacle(self, dynamic_obstacles, robot_future_path):
        """Add dynamic obstacles for a given robots future path."""
        for t_step, pos in enumerate(robot_future_path):
            dynamic_obstacles.add((pos[0], pos[1], t_step))
            # Have other robots avoid entering cell this robot just left. Stops edge collisions.
            dynamic_obstacles.add((pos[0], pos[1], t_step-1))
            # Add a bit more space between robots to avoid rubbing shoulders
            dynamic_obstacles.add((pos[0], pos[1], t_step+1))

    def get_current_static_obstacles(self) -> set[Position]:
        """Return static obstacles with stationary robots too

        Returns a set[Position]: set of (row, col) static obstacles
        """
        # Add stationary robots to static obstacles
        static_obstacles = self.static_obstacles.copy()
        static_obstacles.update(
            robot.pos for robot in self.robots if not robot.future_path)
        return static_obstacles

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
        robot: Robot = self.get_robot(robot_id)
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
            return None  # No available robots

        # Pop task and push into inprogress
        if not self.redis_db.exists('tasks:new') or self.redis_db.llen('tasks:new') == 0:
            return None  # No available tasks
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

        # Returns task_key to tasks:new if it fails
        job = self.make_job(task_key, robot)
        self.logger.info(f'Created Job: {job}')
        return job

    def find_closest_robot_to_position(self, pos: Position, robots: list[Robot]) -> Robot:
        """Returns closest robot to a given position or None if no robots given."""
        closest_robot = None
        closest_dist = None
        for robot in robots:
            dist = abs(pos[0] - robot.pos[0]) + abs(pos[1] - robot.pos[1])
            if not closest_dist or dist < closest_dist:
                closest_dist = dist
                closest_robot = robot
        return closest_robot

    def update(self, robots, t_start, time_left):
        """Process jobs and assign robots tasks.
           If update takes longer than a threshold, the step is skipped and redis is not updated."""
        self.logger.debug('update start')

        # Split amount of time in update for [2] check+update jobs and [3] assign jobs-robots
        time_allotted_for_jobs = time_left * 0.8
        time_allotted_for_assigns = time_left - time_allotted_for_jobs

        # 1 - Update to latest robots from WDB if not passed in
        t_load_robots = time.perf_counter()
        self.robots = self.wdb.get_robots() if robots is None else robots

        def update_too_long():
            """Check if time since t_start > MAX_UPDATE_TIME_SEC"""
            return (time.perf_counter() - t_start) > time_left
        if update_too_long():
            self.logger.warning('update started too late at %.2f ms > %.2f ms threshold, skipping',
                                (time.perf_counter() - t_start)*1000, time_left * 1000)
            return
        t_load_robots = (time.perf_counter() - t_load_robots)*1000
        # Track robots modified in this update step, only update those in redis.
        robot_was_modified: dict[RobotId, bool] = {robot.robot_id: False for robot in self.robots}

        # 2 - Check and update any jobs
        t_update_jobs = time.perf_counter()
        job_keys = list(self.jobs)
        # TODO : Replace this with round-robin
        shuffled_job_keys = random.sample(job_keys, len(job_keys))

        # Get the dynamic obstacles for this timestep
        self.latest_dynamic_obstacles = self.get_all_current_dynamic_obstacles()
        # Only process jobs for up to time_allotted_for_jobs locally and time_left total
        jobs_processed = 0
        processed_jobs: list[Job] = []
        for job_key in shuffled_job_keys:
            if ((time.perf_counter() - t_start) > time_allotted_for_jobs) or update_too_long():
                break
            # Create a copy of the job to be changed
            job = self.jobs[job_key].copy()
            self.check_and_update_job(job)
            jobs_processed += 1
            processed_jobs.append(job)
            robot_was_modified[job.robot_id] = True
        t_update_jobs = (time.perf_counter() - t_update_jobs)*1000

        # 3 - Now check for any available robots and tasks for
        # up to MAX_TIME_ASSIGN_JOB_SEC locally and time_left total
        t_assign = time.perf_counter()
        new_jobs: list[Job] = []
        # Get available robots
        robots_assigned = 0
        available_robots = set(self.get_available_robots())
        available_robots_count = len(available_robots)
        # Get available new tasks
        pipeline = self.redis_db.pipeline()
        pipeline.llen('tasks:new')
        pipeline.lrange('tasks:new', 0, available_robots_count)
        [all_new_tasks_count, new_tasks] = pipeline.execute()
        new_tasks_count = len(new_tasks)
        # For each available pair of robot and tasks
        for idx in range(min(available_robots_count, new_tasks_count)):
            if (time.perf_counter() - t_assign) > time_allotted_for_assigns or update_too_long():
                break
            # Assign new task to available robot, creating a new job
            task_key = new_tasks[idx]
            task_ids = parse_task_key_to_ids(task_key)

            # Get item zone for task, then find robot closest to it
            item_zone = self.item_load_zones[task_ids.item_id]
            robot = self.find_closest_robot_to_position(
                item_zone, available_robots)
            available_robots.remove(robot)
            new_job = self.assign_task_to_robot(task_key, robot)
            new_jobs.append(new_job)
            robots_assigned += 1
            robot_was_modified[new_job.robot_id] = True
        t_assign = (time.perf_counter() - t_assign)*1000

        # Revert changes if at this point update took too long
        # Expectation: No redis writes were done up to this point.
        if update_too_long():
            update_duration_ms = (time.perf_counter() - t_start)*1000
            self.logger.error(
                f'update end, reverted due to over threshold, '
                f'took {update_duration_ms:.3f} ms > {time_left*1000} ms threshold, '
                f'reverting processed {jobs_processed}/{len(shuffled_job_keys)} jobs, '
                f'reverting assigned {robots_assigned}/{available_robots_count} available robots '
                f'to {new_tasks_count}/{all_new_tasks_count} available tasks')
            return

        # 4 - Batch update robots, jobs, tasks now
        t_update_all = time.perf_counter()
        pipeline = self.redis_db.pipeline()
        # Only update those robots that were modified
        modified_robots = [robot for robot in self.robots if robot_was_modified[robot.robot_id]]
        self.wdb.update_robots(modified_robots, pipeline=pipeline)

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
                pipeline.srem('tasks:inprogress', job.task_key)
                pipeline.lpush('tasks:processed', job.task_key)
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
            pipeline.lpop('tasks:new', len(task_keys))
            # Set tasks in progress
            pipeline.sadd('tasks:inprogress', *task_keys)

        # Execute transactions on redis
        pipeline.execute()
        t_update_all = (time.perf_counter() - t_update_all)*1000

        update_duration_ms = (time.perf_counter() - t_start)*1000
        time_used_ratio = update_duration_ms / (time_left*1000)
        self.logger.info(
            f'update end, took {update_duration_ms:.3f} ms of {time_left*1000:.3f} allotted '
            f'({time_used_ratio*100:.1f}% usage), '
            f'processed {jobs_processed}/{len(shuffled_job_keys)} jobs, '
            f'assigned {robots_assigned}/{available_robots_count} available robots '
            f'to {new_tasks_count}/{all_new_tasks_count} available tasks '
            f'[{t_load_robots:.3f}, {t_update_jobs:.3f}, {t_assign:.3f}, {t_update_all:.3f}] ms')

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

        true_dists = self.heuristic_dict[pos_b]

        def true_heuristic(pos_a: Position) -> float:
            """Returns A* shortest path between any two points based on world_grid"""
            return true_dists[pos_a]
        path = pf.st_astar(
            self.world_grid, pos_a, pos_b, dynamic_obstacles, static_obstacles=static_obstacles,
            end_fast=True, max_time=self.max_steps, heuristic=true_heuristic, stats=stats,
            validate_ends=False)
        self.logger.info(
            f'generate_path took {(time.perf_counter() - t_start)*1000:.3f} ms - {stats}')
        return path

    def set_robot_path(self, robot: Robot, path: Path):
        """Sets robot path, and also updates latest dynamic obstacles with this"""
        robot.set_path(path)
        if self.latest_dynamic_obstacles is not None:
            self.add_path_as_obstacle(self.latest_dynamic_obstacles, path)


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
        static_obstacles = self.get_current_static_obstacles()
        job.path_robot_to_item = self.generate_path(
            current_pos, job.item_zone, self.latest_dynamic_obstacles, static_obstacles)
        if not job.path_robot_to_item:
            self.logger.warning(f'Robot {job.robot_id} no path to item zone')

            if job.robot_home == current_pos:
                return False
            # Not at home, so try going home instead for now
            path_to_home = self.generate_path(
                current_pos, job.robot_home, self.latest_dynamic_obstacles, static_obstacles)
            self.logger.warning(
                f'Trying to go home {current_pos} -> {job.robot_home}')
            if path_to_home:
                self.set_robot_path(robot, path_to_home)
                robot.state_description = 'Pathing home, waiting till item zone available'
            return False  # Did not start job as no path existed yet

        self.set_robot_path(robot, job.path_robot_to_item)
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
                self.logger.error(
                    f'Robot {robot.robot_id} path diverged from job pick item, reset state')
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
            job.state = JobState.ERROR
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
        static_obstacles = self.get_current_static_obstacles()
        job.path_item_to_station = self.generate_path(
            current_pos, job.station_zone, self.latest_dynamic_obstacles, static_obstacles)
        if not job.path_item_to_station:
            self.logger.warning('No path to station for %s', job)
            # Try going home instead to leave space at station
            path_to_home = self.generate_path(
                current_pos, job.robot_home, self.latest_dynamic_obstacles, static_obstacles)
            if path_to_home:
                self.set_robot_path(robot, path_to_home)
                robot.state_description = 'Pathing home, waiting till station available'
            return False  # Did not start job as no path existed yet

        # unlock item zone since we're moving
        self.item_locks[job.item_zone] = None

        # Send robot to station
        self.set_robot_path(robot, job.path_item_to_station)
        robot.state_description = 'Pathing to station'
        job.going_to_station()
        self.logger.info(
            f'Sending {robot} to station for task {job.task_key}')
        return True

    def job_drop_item_at_station(self, job: Job) -> bool:
        """Have robot drop item at station if possible."""
        # Check that robot is at station zone
        robot = self.get_robot(job.robot_id)
        if robot.pos != job.station_zone:
            if not robot.future_path:
                self.logger.error(
                    f'Robot {robot.robot_id} path diverged from job drop item, reset state')
                job.state = JobState.ITEM_PICKED
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
            job.state = JobState.ERROR
            return False
        if item_id != job.item_id:
            self.logger.error(
                f"Robot {job.robot_id} was holding the wrong "
                f"item: {item_id}, needed {job.item_id}")
            job.state = JobState.ERROR
            return False

        job.drop_item()
        robot.state_description = f'Finished task: Added item {job.item_id} to station'
        return True

    def job_return_home(self, job: Job) -> bool:
        """Transition to return home state, having robot path home."""
        # Try to generate new path for robot
        robot = self.get_robot(job.robot_id)
        current_pos = robot.pos
        static_obstacles = self.get_current_static_obstacles()
        job.path_station_to_home = self.generate_path(
            current_pos, job.robot_home, self.latest_dynamic_obstacles, static_obstacles)
        if not job.path_station_to_home:
            self.logger.warning(f'Robot {job.robot_id} no path back home')
            return False  # Did not start job as no path existed yet
        # Send robot home
        self.set_robot_path(robot, job.path_station_to_home)
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
                self.logger.error(
                    f'Robot {robot.robot_id} path diverged from job arrive home, reset state')
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

        # Bring robot out of error state and drop any held items
        robot = self.get_robot(job.robot_id)
        robot.state = RobotStatus.IN_PROGRESS
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
        static_obstacles = self.get_current_static_obstacles()
        path_to_home = self.generate_path(
            current_pos, job.robot_home, self.latest_dynamic_obstacles, static_obstacles)
        if path_to_home:
            self.set_robot_path(robot, path_to_home)
        # Set robots start pos to where it is currently
        # job.robot_start_pos = robot.pos
        return False

    def job_restart_manager_return_home(self, job: Job) -> bool:
        """Transition to restart manager return home state, wait for path and then path home."""
        robot = self.get_robot(job.robot_id)
        # Wait for existing path to finish
        if robot.future_path:
            self.logger.warning(
                f'{job} - Robot {job.robot_id} still finishing path')
            return False  # Did not generate path home yet since still have path
        current_pos = robot.pos
        # If path finished at home, we're done here
        if current_pos == job.robot_home:
            job.return_home()
            return self.job_arrive_home(job)
        # Try to find path to home
        static_obstacles = self.get_current_static_obstacles()
        job.path_station_to_home = self.generate_path(
            current_pos, job.robot_home, self.latest_dynamic_obstacles, static_obstacles)
        if not job.path_station_to_home:
            self.logger.warning(f'Robot {job.robot_id} no path back home')
            return False  # Did not start job as no path existed yet
        # Send robot home
        self.set_robot_path(robot, job.path_station_to_home)
        robot.state_description = 'Returning home'
        job.return_home()
        # Release lock on any zones if pos was in them
        if current_pos in self.station_locks:
            self.station_locks[current_pos] = None
        elif current_pos in self.item_locks:
            self.item_locks[current_pos] = None
        self.logger.info(
            f'Sending Robot {job.robot_id} back home for {job.task_key}')
        return True

    # Map states to methods
    state_methods = {
        JobState.WAITING_TO_START: 'job_start',
        JobState.PICKING_ITEM: 'job_try_pick_item',
        JobState.ITEM_PICKED: 'job_go_to_station',
        JobState.GOING_TO_STATION: 'job_drop_item_at_station',
        JobState.ITEM_DROPPED: 'job_return_home',
        JobState.RETURNING_HOME: 'job_arrive_home',
        JobState.COMPLETE: None,
        JobState.RESTART_MGR_GO_HOME: 'job_restart_manager_return_home',
        JobState.ERROR: 'job_restart',
    }

    def check_and_update_job(self, job: Job) -> bool:
        """Process a job based on the current state. """

        # Get the method for the current state
        method_name = self.state_methods.get(job.state)
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
        time_to_next_step_sec = float(data['time_to_next_step_sec'])
        if self.world_sim_t and world_sim_t <= self.world_sim_t:
            # Error out of RA since WS restarted, let RA container restart
            raise ValueError(
                'World time step state earlier than previous, world sim restarted.')
        self.world_sim_t = world_sim_t
        robots = [Robot.from_json(json_data)
                  for json_data in json.loads(data['robots'])]

        self.logger.info(
            f'Step start T={self.world_sim_t} timestamp={timestamp}, '
            f'{time_to_next_step_sec:.1f} sec till next {"-"*100}')
        safe_time_left = time_to_next_step_sec - SAFETY_FACTOR_SEC
        self.update(robots, time_read, safe_time_left)
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

    warehouse_yaml = os.getenv(
        'WAREHOUSE_YAML', 'warehouses/main_warehouse.yaml')

    # Load world info from yaml
    world_info = WorldInfo.from_yaml(warehouse_yaml)
    # Load or build true heuristic dict
    true_heuristic_dict = load_heuristic(warehouse_yaml=warehouse_yaml,
                                         world_info=world_info, logger=logger)

    # Set up redis
    REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))
    redis_con = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    wait_for_redis_connection(redis_con)

    # Init Robot Allocator
    wdb = WorldDatabaseManager(redis_con)  # Contains World/Robot info
    robot_mgr = RobotAllocator(
        logger, redis_con, wdb, world_info, true_heuristic_dict)

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
        except ValueError as e:
            logger.warning('Resetting robot allocator since world_sim restarted')
            robot_mgr = RobotAllocator(logger, redis_con, wdb, world_info, true_heuristic_dict)
