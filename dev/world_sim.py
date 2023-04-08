"""Simulate world grid and robots, updating DB that web server sees."""
from enum import Enum
from typing import List, Tuple, Dict, Optional, Any  # Python 3.8
from datetime import datetime
from time import sleep
import numpy as np
import yaml
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

    def __init__(self, grid: np.ndarray, robots: List[Robot],
                 item_load_zones: List[Position] = [], station_zones: List[Position] = []):
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
        self.ended = False

        self.init_socketio()
        
        world_db_filename = 'world.db' # TODO Move this to config param
        self.wdb = WorldDatabaseManager(world_db_filename)
        self.wdb.reset()
        self.wdb.add_robots(self.robots)

    def get_all_state_data(self):
        return {
            'timestamp': str(datetime.now()),
            't': self.t,
            'grid': self.grid.tolist(),
            'item_load_positions': [{'x': c, 'y': r} for r, c in self.item_load_zones],
            'station_positions': [{'x': c, 'y': r} for r, c in self.station_zones],
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
        self.robots_by_id[robot.id] = len(self.robots)
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
                a1 = robot.get_last_pos()
                self.collision = (robot.id, robot.pos, a1)
                return False

            # vertex conflict
            # Check that no two robots have the same position
            # by building a dict of positions, collision fails out
            if robot.pos in latest_positions:
                other_robot = self.get_robot_by_id(latest_positions[robot.pos])
                a1 = robot.get_last_pos()
                b1 = other_robot.get_last_action()
                self.collision = (robot.id, robot.pos, a1,
                                  other_robot.id, other_robot.pos, b1)
                return False
            else:
                latest_positions[robot.pos] = robot.id

            # edge conflict
            # If robot is entering previously occupied cell, check if other robot moved on same edge
            if robot.pos in self.past_robot_positions:
                other_robot = self.get_robot_by_id(
                    self.past_robot_positions[robot.pos])
                if other_robot == robot:
                    # Same robot, skip
                    continue
                a1 = robot.get_last_pos()
                a2 = robot.pos
                b1 = other_robot.get_last_pos()
                b2 = other_robot.pos
                # Check if robots went directly through each other
                if ((a1 == b2 and a2 == b1)):
                    print(
                        f'Edge collision [{robot}] {a1}->{a2} <-> [{other_robot}] {b1}->{b2}')
                    self.collision = (robot.id, a2, a1,
                                      other_robot.id, b2, b1)
                    return False

        self.collision = None
        return True

    def step(self) -> bool:
        # For every robot in environment, pop an action and apply it
        # check that final state has no robots colliding with walls or
        # each other

        self.robots = self.wdb.get_robots()

        self.past_robot_positions.clear()
        for robot in self.robots:
            self.past_robot_positions[robot.pos] = robot.id

        state_changed = False
        for robot in self.robots:
            state_changed |= robot.move_to_next_position()

        self.world_state = self._check_valid_state()
        self.t += 1

        if state_changed:
            self.wdb.update_robots(self.robots)
        
        self.wdb.update_timestamp(self.t)

        if (state_changed):
            print(f'Robots moved: {self.robots}')

        # Return if any robot has moved or not
        return state_changed

    def show_grid_ascii(self):
        # Create grid string with walls or spaces
        grid_str = np.full_like(self.grid, dtype=str, fill_value='')
        for r in range(self.height):
            for c in range(self.width):
                char = "W" if self.grid[r, c] == EnvType.WALL.value else " "
                grid_str[r, c] += char

        # Place robots in grid_str
        for robot in self.robots:
            r, c = robot.pos
            grid_str[r, c] = (grid_str[r, c] + 'R').strip()
        print("---")
        # Print grid flipped vertically so up down match
        print(np.flipud(grid_str))
        print("---")

    def __repr__(self):
        return f'Env {self.width}x{self.height} [VALID:{self.get_current_state()}]: {self.robots}'


# TODO: Move scenarios to Scenario class
def load_warehouse_yaml(filename: str) -> Tuple[np.ndarray, List[Position], List[Position], List[Position]]:
    with open(filename, 'r', encoding='utf8') as f:
        scenario = yaml.safe_load(f)
    grid = np.array(scenario['grid'])
    robot_home_zones = [(int(r), int(c))
                        for (r, c) in scenario['robot_home_zones']]
    item_load_zones = [(int(r), int(c))
                       for (r, c) in scenario['item_load_zones']]
    station_zones = [(int(r), int(c)) for (r, c) in scenario['station_zones']]
    return grid, robot_home_zones, item_load_zones, station_zones


if __name__ == '__main__':
    grid, robot_home_zones, item_load_zones, station_zones = load_warehouse_yaml(
        'warehouses/warehouse1.yaml')
    # Create robots at start positions
    robots = [Robot(RobotId(i), start_pos)
              for i, start_pos in enumerate(robot_home_zones)]
    world = World(grid, robots, item_load_zones, station_zones)
    print(world)
    world.show_grid_ascii()

    # pylint: disable=invalid-name
    first_time = True
    print('Main loop start...')
    while True:
        world.step()
        print(f'Step {world.t}')
        sleep(1)
