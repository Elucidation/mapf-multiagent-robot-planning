"""Robot class"""
from __future__ import annotations
from enum import Enum
from typing import Tuple, NewType, Optional  # Python 3.8
from collections import deque

from inventory_management_system.Item import ItemId

RobotId = NewType('RobotId', int)
Position = Tuple[int, int]


class RobotStatus(Enum):
    """Robot Status"""
    AVAILABLE = 'AVAILABLE'
    IN_PROGRESS = 'IN_PROGRESS'
    ERROR = 'ERROR'

    @staticmethod
    def load(value: str) -> RobotStatus:
        if value == RobotStatus.AVAILABLE.value:
            return RobotStatus.AVAILABLE
        elif value == RobotStatus.IN_PROGRESS.value:
            return RobotStatus.IN_PROGRESS
        return RobotStatus.ERROR

    def __str__(self):
        return str(self.value)


class Robot(object):
    """Robot has position, id, held items, and a path to follow and methods to do so."""

    def __init__(self, robot_id: RobotId, pos: Position,
                 held_item_id: Optional[ItemId] = None,
                 state: RobotStatus = RobotStatus.AVAILABLE,
                 path: list = []):
        self.id = robot_id
        self.pos = pos  # (X col, Y row)
        self.pos_history: deque = deque(maxlen=10)
        self.held_item_id = held_item_id
        self.state = state
        # Contains future positions
        self.future_path: deque = deque(path)  # deque[(x,y), (x,y), ...]
        self.held_item_id = held_item_id
        self.last_pos = None
        self.reset_position_history()

    def reset_position_history(self):
        """Reset history with current position."""
        self.pos_history.clear()
        self.pos_history.append(self.pos)

    def set_path(self, path):
        """Set future path to given path, removing anything already there."""
        # TODO : Verify legal
        self.future_path = path

    def add_path(self, path):
        """Extend future path with given path."""
        # TODO : Verify path is legal (start is last pos) here?
        self.future_path.extend(path)

    def hold_item(self, item_id: ItemId) -> bool:
        """Set held item if available, bool success."""
        if self.held_item_id is not None:
            return False
        self.held_item_id = item_id
        return True

    def drop_item(self) -> Optional[ItemId]:
        """Drop held item if available, return dropped item if it exists."""
        if self.held_item_id is None:
            return None
        item_id = self.held_item_id
        self.held_item_id = None
        return item_id

    def peek_next_pos(self):
        if not self.future_path:
            return None
        return self.future_path[0]

    def _pop_next_pos(self):
        """Return next position or current if none are there."""
        if not self.future_path:
            return None
        return self.future_path.popleft()

    def get_last_pos(self):
        return self.last_pos

    def move_to_next_position(self):
        """Move to next position if available, bool success."""
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
        return f'Robot_{self.id}[{self.state}] : {self.pos}'

    def json_data(self):
        row, col = self.pos  # x,y = col,row
        return {'id': self.id, 'pos': {'x': col, 'y': row}, 'path': self.future_path}


if __name__ == '__main__':
    robot = Robot(RobotId(0), pos=(0, 1), path=[(1, 1), (2, 1)])
    print(robot.json_data())
