import numpy as np
from enum import Enum
import yaml


# TODO: Move Actions to Action class
class Actions(Enum):
    WAIT = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

# TODO: Make static method in Actions class
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


# TODO: Move scenarios to Scenario class
class EnvType(Enum):
    SPACE = 0
    WALL = 1


def getGridAsEnvironment(grid):
    grid = grid.astype(EnvType)
    grid[grid == 0] = EnvType(0)
    grid[grid == 1] = EnvType(1)
    return grid


def get_scenario(filename):
    with open(filename, 'r') as f:
        scenario = yaml.safe_load(f)
    grid = np.array(scenario['grid'])
    goals = [tuple(x) for x in scenario['goals']]
    starts = [tuple(x) for x in scenario['starts']]
    return grid, goals, starts


def get_scenario_3():
    grid, goals, starts = get_scenario('scenarios/scenario3.yaml')
    grid = getGridAsEnvironment(grid)
    return grid, goals, starts


def get_scenario_4():
    grid, goals, starts = get_scenario('scenarios/scenario4.yaml')
    grid = getGridAsEnvironment(grid)
    return grid, goals, starts


if __name__ == '__main__':
    get_scenario('scenarios/scenario1.yaml')
