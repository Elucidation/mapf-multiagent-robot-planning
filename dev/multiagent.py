import time
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple  # Python 3.8

from multiagent_utils import *
from robot import *
from environment import Environment
import pathfinding
from visualizer import Visualizer

world = Environment(getWorld1(), [])


robot_starts = [(1, 1), (1, 2), (9, 4)]
goals = [(8, 5), (5, 4), (2, 3)]

# robot_starts = [(1, 1), (8, 1)]
# goals = [(7, 2), (1, 2)]
paths = []

for i in range(len(robot_starts)):
    robot = Robot(robot_id=i, pos=robot_starts[i])
    world.add_robot(robot)

    path = pathfinding.astar(
        world.get_int_grid(), robot.pos, goals[i], flip_row_col=True)
    paths.append(path)
    actions = convert_path_to_actions(path)
    for action in actions:
        robot.add_action(action)


# TODO push invalid states into visualization
for i in range(1, 100):
    print(f'--- T{i}')
    state_changed = world.step()
    if not (world.get_current_state()):
        print(f'Invalid state! : {world} : {world.collision}')
    if not state_changed:
        break

visualizer = Visualizer(world.get_int_grid(), robot_starts, goals, paths)
# visualizer.save('test1.gif')
visualizer.show()


