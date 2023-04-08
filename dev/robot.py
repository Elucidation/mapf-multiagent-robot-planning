from enum import Enum
from typing import Tuple, NewType, Optional  # Python 3.8
from collections import deque

RobotId = NewType('RobotId', int)


class Robot(object):
    """Robot position and ID"""

    def __init__(self, robot_id: RobotId, pos: Tuple[int, int], held_item_id: Optional[int] = None, state: str = "", path: list = []):
        self.id = robot_id
        self.pos = pos  # (X col, Y row)
        self.pos_history: deque = deque(maxlen=10)
        self.held_item_id = held_item_id
        self.state = state
        # Contains future positions
        self.future_path: deque = deque(path)
        self.held_item_id = 0
        self.last_pos = None
        self.reset_position_history()

    def reset_position_history(self):
        # Reset history with current position
        self.pos_history.clear()
        self.pos_history.append(self.pos)

    def add_path(self, path):
        # TODO : Verify path is legal (start is last pos) here?
        self.future_path.extend(path)

    def peek_next_pos(self):
        if not self.future_path:
            return None
        return self.future_path[0]

    def _pop_next_pos(self):
        # Return next position or current if none are there
        if not self.future_path:
            return None
        return self.future_path.popleft()

    def get_last_pos(self):
        return self.last_pos

    def move_to_next_position(self):
        # Returns true/false if a move happened
        if not self.future_path:
            return False  # Didn't change
        next_pos = self._pop_next_pos()
        self.last_pos = self.pos
        print(self.pos, next_pos)
        self.pos = next_pos
        # TODO : Consider adding repeated positions to history?
        self.pos_history.append(self.pos)
        return True

    def __repr__(self):
        return (f'Robot_{self.id} : {self.pos}')

    def json_data(self):
        # TODO : get path.
        r, c = self.pos  # x,y = c,r
        return {'id': self.id, 'pos': {'x': c, 'y': r}, 'path': self.future_path}


if __name__ == '__main__':
    robot = Robot(RobotId(0), pos=(0, 1), path=[(1,1),(2,1)])
    print(robot.json_data())
