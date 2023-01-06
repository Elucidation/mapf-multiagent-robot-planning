from enum import Enum
from multiagent_utils import *
from robot import Robot, Action

import numpy as np
from typing import List, Tuple  # Python 3.8
import socketio

class World(object):
    """A grid which robots can be placed and moved in."""

    def __init__(self, grid: np.ndarray, robots: List[Robot]):
        self.grid = grid
        self.height = self.grid.shape[0]  # Rows
        self.width = self.grid.shape[1]  # Cols
        self.robots = robots
        self.robots_by_id: dict = dict()
        self.past_robot_positions: dict = dict()
        self.world_state = True
        self.collision = None

    def setup_socketio(self, address='http://localhost:3000'):
        self.sio = socketio.Client()
        @self.sio.event
        def connect():
            print('Connected')
        @self.sio.event
        def disconnect():
            print('Disconnected')
        @self.sio.event
        def connect_error(data):
            print("The connection failed!")

        self.sio.connect(address)
        self.sio.emit('update',{'test':'example'})

    def add_robot(self, robot: Robot):
        self.robots_by_id[robot.id] = len(self.robots)
        self.robots.append(robot)

    def get_robot_by_id(self, robot_id: int):
        return self.robots[self.robots_by_id[robot_id]]

    def get_grid_tile_for_position(self, pos: Tuple[int, int]):
        # row Y, col X
        return self.grid[pos[1], pos[0]]

    def get_current_state(self):
        # True if valid, false if collision occurred in last step
        return self.world_state

    def _check_valid_state(self):
        latest_positions = dict()
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

    def step(self):
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

        return state_changed

    def get_int_grid(self):
        ngrid = np.zeros_like(self.grid, dtype=int)
        ngrid[self.grid == EnvType.WALL] = 1
        # ngrid[self.grid == EnvType.SPACE] = 0
        return ngrid

    def show_grid_ASCII(self):
        # Create grid string with walls or spaces
        grid_str = np.full_like(self.grid, '')
        for r in range(self.height):
            for c in range(self.width):
                char = "W" if self.grid[r, c] == EnvType.WALL else " "
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

class EnvType(Enum):
    SPACE = 0
    WALL = 1

def getGridAsEnvironment(grid):
    grid = grid.astype(EnvType)
    grid[grid == 0] = EnvType(0)
    grid[grid == 1] = EnvType(1)
    return grid

if __name__ == '__main__':
    grid, goals, starts = get_scenario('scenarios/scenario3.yaml')
    robots = []
    for i, start in enumerate(starts):
        robots.append(Robot(robot_id=i, pos=start))
    grid = getGridAsEnvironment(grid)
    world = World(grid, robots)
    print(world)
    world.show_grid_ASCII()
