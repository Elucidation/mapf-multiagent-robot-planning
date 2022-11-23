import numpy as np
from enum import Enum
import yaml

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

def flip_tuple_lists(abs):
    return [flip_tuple(x) for x in abs]

def flip_tuple_list_of_lists(abss):
    return [flip_tuple_lists(x) for x in abss]


class EnvType(Enum):
    SPACE = 0
    WALL = 1

def get_scenario(filename):
    with open(filename, 'r') as f:
        scenario = yaml.safe_load(f)
    grid = np.array(scenario['grid'])
    goals = [tuple(x) for x in scenario['goals']]
    starts = [tuple(x) for x in scenario['starts']]
    return grid, goals, starts


def get_world_1():
    grid, goals, starts = get_scenario('scenarios/scenario3.yaml')
    # Rows is Y, Cols is X
    grid = grid.astype(EnvType)
    grid[grid==0] = EnvType(0)
    grid[grid==1] = EnvType(1)
    return grid, goals, starts

if __name__ == '__main__':
    getScenario('scenarios/scenario1.yaml')