from multiagent_utils import *
from typing import List, Tuple  # Python 3.8
from collections import deque


class Robot(object):
    """Robot position and ID"""

    def __init__(self, robot_id: int, pos: Tuple[int, int]):
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

    def add_action(self, action: Actions):
        self.actions.append(action)

    def peek_next_action(self):
        if not self.actions:
            return Actions.WAIT
        return self.actions[0]

    def _pop_action(self):
        # Return action or WAIT if none are there
        if not self.actions:
            return Actions.WAIT
        return self.actions.popleft()

    def get_last_action(self):
        return self.last_action

    def do_next_action(self):
        # Returns true if it did an action
        action = self._pop_action()
        self.last_action = action
        if action == Actions.UP:
            self.pos = (self.pos[0], self.pos[1] + 1)
        elif action == Actions.DOWN:
            self.pos = (self.pos[0], self.pos[1] - 1)
        elif action == Actions.LEFT:
            self.pos = (self.pos[0] - 1, self.pos[1])
        elif action == Actions.RIGHT:
            self.pos = (self.pos[0] + 1, self.pos[1])
        elif action == Actions.WAIT:
            pass
        else:
            raise Exception(f'Unexpected action {action}')

        self.pos_history.append(self.pos)
        return action != Actions.WAIT

    def __repr__(self):
        return(f'Robot_{self.id} : {self.pos}')


if __name__ == '__main__':
    robot = Robot(robot_id=0, pos=(0,1))
    print(robot)