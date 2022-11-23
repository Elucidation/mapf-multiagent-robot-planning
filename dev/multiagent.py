import time
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple  # Python 3.8

from multiagent_utils import *
from robot import *
from environment import Environment
import pathfinding
from visualizer import Visualizer

grid, goals, starts = get_world_1()
world = Environment(grid, [])

# These positions are in x/y coords, not r,c
# so we need to flip before passing to MAPF algorithms
starts = [
    (1, 6), (1, 2), (9, 4), (5, 6), (5, 5), (5, 4)]
goals = [
    (9, 5), (5, 4), (1, 4), (1, 3), (5, 3), (1, 5)]

paths = pathfinding.MAPF1(world.get_int_grid(),
                          flip_tuple_lists(starts),
                          flip_tuple_lists(goals),
                          maxiter=100
                          )
paths = flip_tuple_list_of_lists(paths)  # Convert back to XY
collisions = pathfinding.find_all_collisions(paths)
if not collisions:
    print('MAPF1 Found paths without collisions')
else:
    print(f'MAPF1 Collisions: {collisions}')
# print(paths)

for i in range(len(starts)):
    robot = Robot(robot_id=i, pos=starts[i])
    world.add_robot(robot)
    path = paths[i]

    # path = pathfinding.astar(
    #     world.get_int_grid(), robot.pos, goals[i], flip_row_col=True)
    # paths.append(path)
    actions = convert_path_to_actions(path)
    for action in actions:
        robot.add_action(action)


# TODO push invalid states into visualization

# Confirm
for i in range(1, 1+max(map(len, paths))):
    # print(f'--- T{i}')
    state_changed = world.step()
    if not (world.get_current_state()):
        print(f'Invalid state! : {world} : {world.collision}')
    if not state_changed:
        break

visualizer = Visualizer(world.get_int_grid(), starts, goals, paths)
# visualizer.save('test1.gif')
visualizer.show()
