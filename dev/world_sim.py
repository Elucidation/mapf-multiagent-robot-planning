from threading import Thread
import yaml
from enum import Enum
from robot import Robot, Action, RobotId

import numpy as np
from typing import List, Tuple, Dict, Optional, Any  # Python 3.8
import socketio  # type: ignore

from datetime import datetime
from time import sleep


class EnvType(Enum):
    SPACE = 0
    WALL = 1


class World(object):
    """A grid which robots can be placed and moved in."""

    def __init__(self, grid: np.ndarray, robots: List[Robot], item_load_zones: List[Tuple[int, int]] = [], station_zones: List[Tuple[int, int]] = []):
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

        self.t = 0 # world time T
        self.ended = False

        self.init_socketio()

        # Start a thread to try and repeatedly connet to socketio
        self.thread = self.connect_socketio()

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
        # Client sends messages to NodeJs web server
        self.sio_client = socketio.Client(logger=True)
        # Server listens for Robot allocator client
        self.sio_server = socketio.Server(logger=True)

        @self.sio_client.event
        def connect():
            print('Connected')

        @self.sio_client.event
        def disconnect():
            print('Disconnected')

        @self.sio_client.event
        def connect_error(data):
            print("-Connect error-")

    def connect_socketio(self, address='http://localhost:3000') -> Thread:
        def wait_till_socketio_connected():
            while not self.ended:
                try:
                    self.sio_client.connect(address)
                    print('SIO - Connected as ', self.sio_client.sid)
                    break
                except socketio.exceptions.ConnectionError:
                    if self.ended:
                        break
                    print('SIO - No connection yet, Sleeping...')
                    self.sio_client.sleep(5)

        print('Trying to connect to', address)
        thread = self.sio_client.start_background_task(wait_till_socketio_connected)
        return thread

    def send_socketio_message(self, topic: str, data):
        # Example emit
        self.sio_client.emit(topic, data)
        print('Sent message to nodejs')

    def add_robot(self, robot: Robot):
        self.robots_by_id[robot.id] = len(self.robots)
        self.robots.append(robot)

    def get_robot_by_id(self, robot_id: int):
        return self.robots[self.robots_by_id[robot_id]]

    def get_grid_tile_for_position(self, pos: Tuple[int, int]) -> EnvType:
        # row Y, col X
        return EnvType(self.grid[pos[1], pos[0]])

    def get_current_state(self) -> bool:
        # True if valid, false if collision occurred in last step
        return self.world_state

    def _check_valid_state(self) -> bool:
        latest_positions: Dict[Tuple[int, int], RobotId] = dict()
        for robot in self.robots:
            # Check robot on space tile (not a wall)
            grid_val = self.get_grid_tile_for_position(robot.pos)
            if grid_val != EnvType.SPACE:
                a1 = robot.get_last_action()
                self.collision = (robot.id, robot.pos, a1)
                return False

            # vertex conflict
            # Check that no two robots have the same position
            # by building a dict of positions, collision fails out
            if robot.pos in latest_positions:
                other_robot = self.get_robot_by_id(latest_positions[robot.pos])
                a1 = robot.get_last_action()
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
                a1 = robot.get_last_action()
                b1 = other_robot.get_last_action()

                # Check for the two types of edge collisions, left/right and up/down
                if ((a1 == Action.LEFT and b1 == Action.RIGHT) or
                    (a1 == Action.RIGHT and b1 == Action.LEFT) or
                    (a1 == Action.UP and b1 == Action.DOWN) or
                        (a1 == Action.DOWN and b1 == Action.UP)):
                    print(
                        f'Edge collision [{robot}] {a1} <-> [{other_robot}] {b1}')
                    self.collision = (robot.id, robot.pos, a1,
                                      other_robot.id, other_robot.pos, b1)
                    return False

            #     pass # TODO check going through each-other collision

        self.collision = None
        return True

    def step(self) -> bool:
        # For every robot in environment, pop an action and apply it
        # check that final state has no robots colliding with walls or
        # each other

        self.past_robot_positions.clear()
        for robot in self.robots:
            self.past_robot_positions[robot.pos] = robot.id

        state_changed = False
        for robot in self.robots:
            state_changed |= robot.do_next_action()

        self.world_state = self._check_valid_state()
        self.t += 1

        return state_changed

    def show_grid_ASCII(self):
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
        return (f'Env {self.width}x{self.height} [VALID:{self.get_current_state()}]: {self.robots}')

    def __del__(self):
        self.ended = True
        del self.sio_client
        del self.thread


# TODO: Move scenarios to Scenario class

def load_warehouse_yaml(filename: str) -> Tuple[np.ndarray, List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[int, int]]]:
    with open(filename, 'r') as f:
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
        'dev/warehouses/warehouse1.yaml')
    # Create robots at start positions
    robots = [Robot(RobotId(i), start_pos)
              for i, start_pos in enumerate(robot_home_zones)]
    world = World(grid, robots, item_load_zones, station_zones)
    print(world)
    world.show_grid_ASCII()

    try:
        first_time = True
        print('Main loop start...')
        while True:
            # Arbitrarily change robot positions
            world.robots[0].add_action(Action.RIGHT if world.t % 2 == 0 else Action.LEFT)
            world.step()
            print(f'Step {world.t}')
            if world.sio_client.connected:
                if first_time:
                    world.send_socketio_message(
                        topic='world_sim_static_update',
                        data=world.get_all_state_data())
                    first_time = False

                world.send_socketio_message(
                    topic='world_sim_robot_update',
                    data=world.get_position_update_data())
            sleep(10)
    except KeyboardInterrupt:
        print('Breaking out')
        world.ended = True
        world.sio_client.disconnect()
