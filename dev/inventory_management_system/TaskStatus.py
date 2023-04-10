"""Task Status"""
from __future__ import annotations
from enum import Enum


class TaskStatus(Enum):
    """Task Status"""
    OPEN = 'OPEN'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETE = 'COMPLETE'
    ERROR = 'ERROR'

    @staticmethod
    def load(value: str) -> TaskStatus:
        if value == TaskStatus.OPEN:
            return TaskStatus.OPEN
        elif value == TaskStatus.IN_PROGRESS:
            return TaskStatus.IN_PROGRESS
        elif value == TaskStatus.COMPLETE:
            return TaskStatus.COMPLETE

        return TaskStatus.ERROR

    def __str__(self):
        return str(self.value)
