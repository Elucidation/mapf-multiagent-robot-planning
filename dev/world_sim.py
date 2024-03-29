"""Simulate world grid and robots, updating DB that web server sees."""
from enum import Enum
from collections import Counter
import functools
import json
import sys
from typing import List, Tuple, Dict, Optional, Any  # Python 3.8
from datetime import datetime
import logging
import os
import time
import numpy as np
from warehouse_logger import create_warehouse_logger
from warehouses.warehouse_loader import load_warehouse_yaml
from robot import Robot, RobotId
from world_db import WorldDatabaseManager
import redis  # type: ignore
# pylint: disable=redefined-outer-name


# Force Win10 timer to be accurate to 1ms (defaults to ~10-14ms accuracy otherwise)
if os.name == 'nt':
    import ctypes
    winmm = ctypes.WinDLL('winmm')
    winmm.timeBeginPeriod(1)

Position = Tuple[int, int]

# TODO : Consolidate timeit and have all modules use the same one.
# Decorator for timing functions


def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f'{func.__name__!r} Start')
        t_start = time.perf_counter()
        result = func(*args, **kwargs)
        t_end = time.perf_counter()
        logger.debug(
            f'{func.__name__!r} End. Took {(t_end - t_start)*1000:.3f} ms')
        return result
    return wrapper


class EnvType(Enum):
    """grid labels for obstacles and spaces."""
    SPACE = 0
    WALL = 1


class World(object):
    """A grid which robots can be placed and moved in."""

    def __init__(self, grid: np.ndarray, robots: List[Robot], time_step_sec: float,
                 redis_con: redis.Redis, item_load_zones: List[Position] = [],
                 station_zones: List[Position] = [], logger=logging):
        self.logger = logger
        self.logger.debug('World init start')
        self.grid = grid
        self.height = self.grid.shape[0]  # Rows
        self.width = self.grid.shape[1]  # Cols
        self.robots: List[Robot] = []
        self.robots_by_id: dict = dict()
        for robot in robots:
            self.add_robot(robot)

        self.past_robot_positions: dict = dict()
        self.world_state = True
        self.collisions: Optional[Any] = None
        self.item_load_zones = item_load_zones
        self.station_zones = station_zones

        self.t = 0  # world time T
        self.last_step_start_time: Optional[float] = None
        self.dt_sec = time_step_sec  # expected time step in seconds with self.sleep()
        self.ended = False

        self.wdb = WorldDatabaseManager(redis_con)

        self.logger.debug('World initialized')

    def reset(self):
        self.wdb.reset()
        self.wdb.add_robots(self.robots)
        self.wdb.set_dt_sec(self.dt_sec)

    def update_timestamp_from_db(self):
        self.t = self.wdb.get_timestamp()

    def update_dt_from_db(self):
        self.dt_sec = self.wdb.get_dt_sec()

    def state_dict_full(self):
        return {
            't': self.t,
            'timestamp': str(datetime.now()),
            'grid': self.grid.tolist(),
            'item_load_positions': [{'x': c, 'y': row} for row, c in self.item_load_zones],
            'station_positions': [{'x': c, 'y': row} for row, c in self.station_zones],
            'robots': json.dumps([robot.json_data() for robot in self.robots])
        }

    def state_dict(self, robots_json_data, time_to_next_step_sec=None):
        """Returns a dict with the t, and robot jsons"""
        return {
            't': self.t,
            'time_to_next_step_sec': time_to_next_step_sec,
            'robots': json.dumps(robots_json_data)
        }

    def add_robot(self, robot: Robot):
        self.robots_by_id[robot.robot_id] = len(self.robots)
        self.robots.append(robot)

    def get_robot_by_id(self, robot_id: int):
        return self.robots[self.robots_by_id[robot_id]]

    def get_grid_tile_for_position(self, pos: Position) -> EnvType:
        # row Y, col X
        return EnvType(self.grid[pos[1], pos[0]])

    def get_current_state(self) -> bool:
        # True if valid, false if collision occurred in last step
        return self.world_state

    @timeit
    def _check_valid_state(self) -> bool:
        latest_positions: Dict[Position, RobotId] = dict()
        self.collisions = []
        for robot in self.robots:
            # Check robot on space tile (not a wall)
            grid_val = self.get_grid_tile_for_position(robot.pos)
            if grid_val != EnvType.SPACE:
                past_pos = robot.get_last_pos()
                self.collisions.append({
                    robot.robot_id: {
                        'pos': robot.pos,
                        'prev_pos': past_pos,
                    },
                    'type': 'Hit wall'})

            # vertex conflict
            # Check that no two robots have the same position
            # by building a dict of positions, collision fails out
            if robot.pos in latest_positions:
                other_robot = self.get_robot_by_id(latest_positions[robot.pos])
                past_pos = robot.get_last_pos()
                other_robot_past_pos = other_robot.get_last_pos()
                self.collisions.append({
                    robot.robot_id: {
                        'pos': robot.pos,
                        'prev_pos': past_pos,
                    },
                    other_robot.robot_id: {
                        'pos': other_robot.pos,
                        'prev_pos': other_robot_past_pos
                    },
                    'type': '2R C'})
            else:
                latest_positions[robot.pos] = robot.robot_id

            # edge conflict
            # If robot is entering previously occupied cell, check if other robot moved on same edge
            if robot.pos in self.past_robot_positions:
                other_robot = self.get_robot_by_id(
                    self.past_robot_positions[robot.pos])
                if other_robot == robot:
                    # Same robot, skip
                    continue
                r1_past = robot.get_last_pos()
                r1_now = robot.pos
                r2_past = other_robot.get_last_pos()
                r2_now = other_robot.pos
                # Check if robots went directly through each other
                if (r1_past == r2_now and r1_now == r2_past):
                    self.collisions.append({
                        robot.robot_id: {
                            'pos': r1_now,
                            'prev_pos': r1_past,
                        },
                        other_robot.robot_id: {
                            'pos': r2_now,
                            'prev_pos': r2_past
                        },
                        'type': '2R C-C'})

        return self.collisions == []

    def step_robots(self) -> list[bool]:
        """Step robots, and return a bool list of those robots that changed positions."""
        self.past_robot_positions.clear()
        for robot in self.robots:
            self.past_robot_positions[robot.pos] = robot.robot_id

        state_changed = [False] * len(self.robots)
        for idx, robot in enumerate(self.robots):
            state_changed[idx] = robot.move_to_next_position()
        return state_changed

    @timeit
    def step(self) -> bool:
        # For every robot in environment, pop an action and apply it
        # check that final state has no robots colliding with walls or
        # each other
        self.logger.debug('Step start')
        t_start = time.perf_counter()
        self.last_step_start_time = t_start

        self.robots = self.wdb.get_robots()

        state_changed = self.step_robots()

        self.world_state = self._check_valid_state()
        self.t += 1

        time_to_next_step_sec = self.get_time_to_next_step_s()
        robots_json_data = [robot.json_data() for robot in self.robots]
        json_data = self.state_dict(robots_json_data, time_to_next_step_sec)

        if any(state_changed):
            changed_robots = [robot for robot, changed in zip(self.robots, state_changed) if changed]
            changed_robots_json_data = [robot_json for robot_json, changed in zip(robots_json_data, state_changed) if changed]
            self.wdb.update_robots(changed_robots, robots_json_data=changed_robots_json_data)

        self.wdb.update_timestamp(self.t)
        # Log state of world (t and robot info) to DB
        self.wdb.log_world_state(json_data)
        update_duration_ms = (time.perf_counter() - t_start)*1000

        self.logger.debug(
            f'Step end, took {update_duration_ms:.3f} ms: '
            f'T={self.t} VALID={self.world_state} state change={state_changed}')
        if update_duration_ms > self.dt_sec*1000:
            self.logger.error(
                f'update took {update_duration_ms:.2f} > {self.dt_sec*1000} ms')
        # Return if any robot has moved or not
        return any(state_changed)

    def get_time_to_next_step_s(self) -> float:
        """Returns the estimated time in seconds till the next step."""
        delay = self.dt_sec
        if self.last_step_start_time:
            # Get delay needed to reach next time step based on the start of the last
            delay = self.dt_sec - \
                (time.perf_counter() - self.last_step_start_time)
            # If that time already passed, push delay as many time steps needed.
            while delay <= 0:
                delay += self.dt_sec
        return delay

    def sleep(self):
        delay = self.get_time_to_next_step_s()
        logger.debug(f'sleep for {delay} sec')
        time.sleep(delay)

    def get_grid_ascii(self):
        # Create grid string with walls or spaces
        np.set_printoptions(linewidth=200, suppress=True)
        grid_str = np.full_like(self.grid, dtype=str, fill_value='')
        for row in range(self.height):
            for col in range(self.width):
                char = "W" if self.grid[row,
                                        col] == EnvType.WALL.value else " "
                grid_str[row, col] += char

        # Place robots in grid_str
        for robot in self.robots:
            col, row = robot.pos
            grid_str[row, col] = (grid_str[row, col] + 'R').strip()

        grid_str_flip = np.flipud(grid_str)
        grid_msg = '\n'.join([''.join(row) for row in grid_str_flip])
        # Print grid flipped vertically so up down match
        msg = f"---\n{grid_msg}\n---"
        return msg

    def __repr__(self):
        return f'Env {self.width}x{self.height} [VALID:{self.get_current_state()}]: {self.robots}'


def wait_for_redis_connection(redis_con):
    while True:
        try:
            if redis_con.ping():
                break
            else:
                logger.warning(
                    f'Ping failed for redis server {REDIS_HOST}:{REDIS_PORT}, waiting')
        except redis.ConnectionError:
            logger.error(
                f'Redis unable to connect {REDIS_HOST}:{REDIS_PORT}, waiting')
        time.sleep(2)


if __name__ == '__main__':
    logger = create_warehouse_logger('world_sim')

    # Set up redis
    REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))
    redis_con = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    logger.info(f'Connecting to redis server {REDIS_HOST}:{REDIS_PORT}')
    # Note this will fail if redis server not accessible
    wait_for_redis_connection(redis_con)

    grid, robot_home_zones, item_load_zones, station_zones = load_warehouse_yaml(
        os.getenv('WAREHOUSE_YAML', 'warehouses/main_warehouse.yaml'))
    logger.info(
        f'World Shape: {grid.shape}, {len(robot_home_zones)} robots,'
        f' {len(item_load_zones)} item zones, {len(station_zones)} stations')

    # Create robots at start positions (row,col) -> (x,y)
    robots = [Robot(RobotId(i), (col, row))
              for i, (row, col) in enumerate(robot_home_zones)]

    TIME_STEP_SEC = float(os.getenv("TIME_STEP_SEC", default="1"))
    world = World(grid, robots, TIME_STEP_SEC, redis_con, item_load_zones,
                  station_zones, logger=logger)
    if 'reset' in sys.argv:
        print('Resetting database')
        world.reset()
    else:
        logger.info('Loading time and dt from DB')
        world.update_timestamp_from_db()
        world.update_dt_from_db()
    logger.info(f'World start: T = {world.t}, DT = {world.dt_sec}')
    # logger.info(world)
    # logger.info(world.get_grid_ascii())

    logger.info('Main loop start...')
    while True:
        t_start = time.perf_counter()
        world.step()
        step_duration_ms = (time.perf_counter() - t_start)*1000
        state_counts = Counter([robot.state for robot in world.robots])
        state_counts_str = ','.join(f'{state}:{count}' for state, count in state_counts.items())
        logger.info(
            f'Step {world.t} - took {step_duration_ms:.3f} ms - States: [{state_counts_str}]')
        if not world.get_current_state():
            logger.error(
                f'World State invalid {len(world.collisions)} collisions. '
                f'first 10 collision(s): {world.collisions[:10]}')
        world.sleep()
