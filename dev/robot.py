"""Robot class"""
from __future__ import annotations
from enum import Enum
import json
from typing import Tuple, NewType, Optional  # Python 3.8
from collections import deque

from inventory_management_system.Item import ItemId

RobotId = NewType('RobotId', int)
Position = Tuple[int, int]
Path = list[Position]


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
                 path: list = [], task_key = '', state_description = 'Initialized'):
        self.robot_id = robot_id
        self.pos = (int(pos[0]), int(pos[1]))  # (X col, Y row)
        self.held_item_id = held_item_id
        self.state = state
        # Contains future positions
        self.future_path: list = path  # deque[(x,y), (x,y), ...]
        self.held_item_id = held_item_id
        self.last_pos = None
        self.task_key = task_key
        self.state_description = state_description

    def set_path(self, path: Path):
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

    def get_last_pos(self):
        return self.last_pos

    def move_to_next_position(self):
        """Move to next position if available, bool success."""
        if not self.future_path:
            return False  # Didn't change
        self.last_pos = self.pos
        self.pos = self.future_path.pop(0)
        return True

    def __repr__(self):
        if self.held_item_id is not None:
            return f'Robot_{self.robot_id}[{self.state} H:{self.held_item_id}] : {self.pos}'
        return f'Robot_{self.robot_id}[{self.state}] : {self.pos}'

    def json_data(self):
        return {'robot_id': self.robot_id,
                'position': json.dumps(self.pos),
                'held_item_id': self.held_item_id if self.held_item_id is not None else '',
                'state': self.state.value,
                'task_key': self.task_key or '',
                'state_description': self.state_description or '',
                'path': json.dumps(self.future_path),
                }

    @staticmethod
    def from_json(json_data: str):
        future_path = [tuple(pos) for pos in json.loads(json_data['path'])]
        held_item_id = ItemId(int(json_data['held_item_id'])) if json_data['held_item_id'] != '' else None
        state_description = json_data['state_description'] if json_data['state_description'] else ''
        return Robot(RobotId(int(json_data['robot_id'])),
                     tuple(json.loads(json_data['position'])),
                     held_item_id,
                     RobotStatus.load(json_data['state']),
                     future_path,
                     json_data['task_key'],
                     state_description)


if __name__ == '__main__':
    robot = Robot(RobotId(0), pos=(0, 1), path=[(1, 1), (2, 1)])
    print(robot.json_data())
    robot2 = Robot.from_json(robot.json_data())
    print(robot)
    print(robot2)