import numpy as np
from enum import Enum


class Actions(Enum):
    WAIT = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4


def convert_path_to_actions(path):
    # path is a list of tuple r,c indices
    actions = []
    for i in range(len(path)-1):
        change = (path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
        # switch r,c to x,y
        # change = (change[1], change[0])

        if change == (0, 1):
            actions.append(Actions.UP)
        elif change == (0, -1):
            actions.append(Actions.DOWN)
        elif change == (-1, 0):
            actions.append(Actions.LEFT)
        elif change == (1, 0):
            actions.append(Actions.RIGHT)
        elif change == (0, 0):
            actions.append(Actions.WAIT)
        else:
            raise Exception(f'Path {change} not allowed')
    return actions


def flip_tuple(ab):
    return (ab[1], ab[0])


class EnvType(Enum):
    SPACE = 0
    WALL = 1


def getWorld1():
    W = EnvType.WALL
    S = EnvType.SPACE

    # Rows is Y, Cols is X
    grid = np.array([
        [W, W, W, W, W, W, W, W, W, W, W],
        [W, S, S, S, S, S, S, S, S, S, W],
        [W, S, S, S, S, S, S, S, S, S, W],
        [W, S, S, S, W, S, W, W, S, S, W],
        [W, S, S, S, W, S, W, W, S, S, W],
        [W, S, S, S, W, S, W, W, S, S, W],
        [W, S, S, S, W, S, W, W, S, S, W],
        [W, S, S, S, W, S, W, W, S, S, W],
        [W, S, S, S, S, S, S, S, S, S, W],
        [W, S, S, S, S, S, S, S, S, S, W],
        [W, W, W, W, W, W, W, W, W, W, W],
    ], dtype=EnvType)
    return grid
