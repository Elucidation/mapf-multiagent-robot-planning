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


# These positions are in x/y coords, not r,c
# so we need to flip before passing to MAPF algorithms
robot_starts = [(1, 1), (1, 2), (9, 4)]
goals = [(8, 5), (5, 4), (2, 3)]

paths = pathfinding.MAPF1(world.get_int_grid(),
    flip_tuple_lists(robot_starts),
    flip_tuple_lists(goals)
    )
paths = flip_tuple_list_of_lists(paths) # Convert back to XY

for i in range(len(robot_starts)):
    robot = Robot(robot_id=i, pos=robot_starts[i])
    world.add_robot(robot)
    path = paths[i]

    # path = pathfinding.astar(
    #     world.get_int_grid(), robot.pos, goals[i], flip_row_col=True)
    # paths.append(path)
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
visualizer.save('test1.gif')
visualizer.show()


