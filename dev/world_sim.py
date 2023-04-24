"""Simulate world grid and robots, updating DB that web server sees."""
from enum import Enum
from typing import List, Tuple, Dict, Optional, Any  # Python 3.8
from datetime import datetime
import logging
import time
import numpy as np
from warehouses.warehouse_loader import load_warehouse_yaml
from robot import Robot, RobotId
from world_db import WorldDatabaseManager
import socketio  # type: ignore
# pylint: disable=redefined-outer-name


Position = Tuple[int, int]


class EnvType(Enum):
    """grid labels for obstacles and spaces."""
    SPACE = 0
    WALL = 1


class World(object):
    """A grid which robots can be placed and moved in."""

    def __init__(self, grid: np.ndarray, robots: List[Robot], time_step_sec: float,
                 item_load_zones: List[Position] = [], station_zones: List[Position] = [],
                 logger=logging):
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
        self.collision: Optional[Any] = None
        self.item_load_zones = item_load_zones
        self.station_zones = station_zones

        self.t = 0  # world time T
        self.last_step_start_time: Optional[float] = None
        self.dt_sec = time_step_sec  # expected time step in seconds with self.sleep()
        self.ended = False

        self.init_socketio()

        world_db_filename = 'world.db'  # TODO Move this to config param
        self.wdb = WorldDatabaseManager(world_db_filename)
        self.wdb.reset()
        self.wdb.add_robots(self.robots)
        self.wdb.set_dt_sec(self.dt_sec)
        self.logger.debug('World initialized')

    def get_all_state_data(self):
        return {
            'timestamp': str(datetime.now()),
            't': self.t,
            'grid': self.grid.tolist(),
            'item_load_positions': [{'x': c, 'y': row} for row, c in self.item_load_zones],
            'station_positions': [{'x': c, 'y': row} for row, c in self.station_zones],
            'robots': [r.json_data() for r in self.robots]
        }

    def get_position_update_data(self):
        return {
            'timestamp': str(datetime.now()),
            't': self.t,
            'robots': [r.json_data() for r in self.robots]
        }

    def init_socketio(self):
        # TODO : Server listens for Robot allocator client
        self.sio_server = socketio.Server(logger=True)

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

    def _check_valid_state(self) -> bool:
        latest_positions: Dict[Position, RobotId] = dict()
        for robot in self.robots:
            # Check robot on space tile (not a wall)
            grid_val = self.get_grid_tile_for_position(robot.pos)
            if grid_val != EnvType.SPACE:
                self.collision = (robot.robot_id, robot.pos,
                                  robot.get_last_pos())
                self.logger.error(
                    f'Robot collided with non-space tile {self.collision}')
                return False

            # vertex conflict
            # Check that no two robots have the same position
            # by building a dict of positions, collision fails out
            if robot.pos in latest_positions:
                other_robot = self.get_robot_by_id(latest_positions[robot.pos])
                past_pos = robot.get_last_pos()
                other_robot_past_pos = other_robot.get_last_pos()
                self.collision = (robot.robot_id, robot.pos, past_pos,
                                  other_robot.robot_id, other_robot.pos, other_robot_past_pos)
                self.logger.error(f'Robot collision {self.collision}')
                return False
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
                    self.logger.error(
                        f'Edge collision [{robot}] {r1_past}->{r1_now} <->'
                        f' [{other_robot}] {r2_past}->{r2_now}')
                    self.collision = (robot.robot_id, r1_now, r1_past,
                                      other_robot.robot_id, r2_now, r2_past)
                    return False

        self.collision = None
        return True

    def step(self) -> bool:
        # For every robot in environment, pop an action and apply it
        # check that final state has no robots colliding with walls or
        # each other
        self.logger.debug('Step start')
        t_start = time.perf_counter()
        self.last_step_start_time = t_start

        self.robots = self.wdb.get_robots()

        self.past_robot_positions.clear()
        for robot in self.robots:
            self.past_robot_positions[robot.pos] = robot.robot_id

        state_changed = False
        for robot in self.robots:
            state_changed |= robot.move_to_next_position()

        self.world_state = self._check_valid_state()
        self.t += 1

        if state_changed:
            self.wdb.update_robots(self.robots)

        self.wdb.update_timestamp(self.t)

        if state_changed:
            self.logger.debug(f'Robots moved: {self.robots}')

        self.logger.debug(
            f'Step end, took {time.perf_counter() - t_start:.6f} sec: '
            f'T={self.t} VALID={self.world_state} state change={state_changed}')
        # Return if any robot has moved or not
        return state_changed

    def sleep(self):
        delay = self.dt_sec
        if self.last_step_start_time:
            delay = max(0, self.dt_sec - (time.perf_counter() - self.last_step_start_time))
        time.sleep(delay)

    def get_grid_ascii(self):
        # Create grid string with walls or spaces
        grid_str = np.full_like(self.grid, dtype=str, fill_value='')
        for row in range(self.height):
            for col in range(self.width):
                char = "W" if self.grid[row,
                                        col] == EnvType.WALL.value else " "
                grid_str[row, col] += char

        # Place robots in grid_str
        for robot in self.robots:
            row, col = robot.pos
            grid_str[row, col] = (grid_str[row, col] + 'R').strip()

        # Print grid flipped vertically so up down match
        msg = f"---\n{np.flipud(grid_str)}\n---"
        return msg

    def __repr__(self):
        return f'Env {self.width}x{self.height} [VALID:{self.get_current_state()}]: {self.robots}'


def create_logger():
    logging.basicConfig(filename='world_sim.log', encoding='utf-8', filemode='w',
                        level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('world_sim')
    logger.setLevel(logging.DEBUG)
    stream_logger = logging.StreamHandler()
    stream_logger.setLevel(logging.INFO)
    logger.addHandler(stream_logger)
    return logger


if __name__ == '__main__':
    logger = create_logger()
    TIME_STEP_SEC = 0.1
    logger.debug(f'TIME_STEP_SEC = {TIME_STEP_SEC}')

    grid, robot_home_zones, item_load_zones, station_zones = load_warehouse_yaml(
        'warehouses/warehouse3.yaml')
    # Create robots at start positions (row,col) -> (x,y)
    robots = [Robot(RobotId(i), (col, row))
              for i, (row, col) in enumerate(robot_home_zones)]
    world = World(grid, robots, TIME_STEP_SEC, item_load_zones,
                  station_zones, logger=logger)
    logger.info(world)
    logger.info(world.get_grid_ascii())

    # pylint: disable=invalid-name
    first_time = True
    logger.info('Main loop start...')
    while True:
        world.step()
        logger.info(f'Step {world.t}')
        world.sleep()
