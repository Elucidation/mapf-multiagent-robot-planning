from multiagent_utils import *
from robot import *
from environment import Environment
import pathfinding

import time
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple  # Python 3.8

###########


def init_viz():
    # print(world)
    # world.show_grid_ASCII()

    plt.ion()

    # ngrid = world.get_int_grid()
    mainfig = plt.figure()
    # plt.imshow(ngrid, aspect='equal', interpolation='none', origin='lower')
    # plt.pause(0.05)
    # plt.show()


def show_state(title=''):
    # print(world)
    # world.show_grid_ASCII()
    plt.clf()

    ngrid = world.get_int_grid()
    # fig = plt.figure()
    plt.imshow(ngrid, aspect='equal', interpolation='none', origin='lower')

    offset = 0.2 / len(world.robots)
    for i, robot in enumerate(world.robots):

        # Show path line for each robot
        pos_history = np.array(robot.pos_history)
        plt.plot(pos_history[:, 0] + i*offset,
                 pos_history[:, 1] + i*offset, '.-')

        # Add text for markers
        # for k, pos in enumerate(pos_history):
        #     plt.text(pos[0]+i*offset, pos[1]+i*offset, k, size=6, color='w')
    for i, robot in enumerate(world.robots):
        # Show circle for current robot location
        plt.plot(robot.pos[0], robot.pos[1], 'ro', markersize=15)
        # Label bot
        plt.text(robot.pos[0]-0.1, robot.pos[1] -
                 0.1, robot.id, size=10, color='w')
    # plt.draw()
    plt.title(title)
    plt.pause(0.05)


#######################
world = Environment(getWorld1(), [])


robot_starts = [(1, 1), (1, 2), (9, 4)]
goals = [(8, 5), (5, 4), (2, 3)]

# robot_starts = [(1, 1), (8, 1)]
# goals = [(7, 2), (1, 2)]


for i in range(len(robot_starts)):
    robot = Robot(robot_id=i, pos=robot_starts[i])
    world.add_robot(robot)

    path = pathfinding.astar(
        world.get_int_grid(), robot.pos, goals[i], flip_row_col=True)
    actions = convert_path_to_actions(path)
    for action in actions:
        robot.add_action(action)


init_viz()
show_state(title='T=0')
time_step = 0.5
time.sleep(time_step)


for i in range(1, 100):
    print(f'--- T{i}')
    state_changed = world.step()
    show_state(title=f'T={i} Valid:{world.get_current_state()}')
    if not (world.get_current_state()):
        print(f'Invalid state! : {world} : {world.collision}')
    time.sleep(time_step)
    if not state_changed:
        break

plt.ioff()
plt.show()
