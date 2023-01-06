from enum import Enum
from multiagent_utils import *
from typing import Tuple, NewType  # Python 3.8
from collections import deque


class Action(Enum):
    # TODO: Move Actions to Action class
    WAIT = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

    @staticmethod
    def convert_path_to_actions(path):
        # path is a list of tuple r,c indices
        actions = []
        for i in range(len(path)-1):
            change = (path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
            # switch r,c to x,y
            # change = (change[1], change[0])

            if change == (0, 1):
                actions.append(Action.UP)
            elif change == (0, -1):
                actions.append(Action.DOWN)
            elif change == (-1, 0):
                actions.append(Action.LEFT)
            elif change == (1, 0):
                actions.append(Action.RIGHT)
            elif change == (0, 0):
                actions.append(Action.WAIT)
            else:
                raise Exception(f'Path {change} not allowed')
        return actions


RobotId = NewType('RobotId', int)


class Robot(object):
    """Robot position and ID"""

    def __init__(self, robot_id: RobotId, pos: Tuple[int, int]):
        self.id = robot_id
        self.pos = pos  # (X col, Y row)
        self.pos_history: deque = deque(maxlen=10)
        self.actions: deque = deque()
        self.last_action = None
        self.reset_position_history()

    def reset_position_history(self):
        # Reset history with current position
        self.pos_history.clear()
        self.pos_history.append(self.pos)

    def add_action(self, action: Action):
        self.actions.append(action)

    def peek_next_action(self):
        if not self.actions:
            return Action.WAIT
        return self.actions[0]

    def _pop_action(self):
        # Return action or WAIT if none are there
        if not self.actions:
            return Action.WAIT
        return self.actions.popleft()

    def get_last_action(self):
        return self.last_action

    def do_next_action(self):
        # Returns true if it did an action
        action = self._pop_action()
        self.last_action = action
        if action == Action.UP:
            self.pos = (self.pos[0], self.pos[1] + 1)
        elif action == Action.DOWN:
            self.pos = (self.pos[0], self.pos[1] - 1)
        elif action == Action.LEFT:
            self.pos = (self.pos[0] - 1, self.pos[1])
        elif action == Action.RIGHT:
            self.pos = (self.pos[0] + 1, self.pos[1])
        elif action == Action.WAIT:
            pass
        else:
            raise Exception(f'Unexpected action {action}')

        self.pos_history.append(self.pos)
        return action != Action.WAIT

    def __repr__(self):
        return (f'Robot_{self.id} : {self.pos}')

    def json_data(self):
        # TODO : get path.
        r,c = self.pos # x,y = c,r
        return {'id': self.id, 'pos': {'x': c, 'y': r}, 'path': []}


if __name__ == '__main__':
    robot = Robot(RobotId(0), pos=(0, 1))
    print(robot)
