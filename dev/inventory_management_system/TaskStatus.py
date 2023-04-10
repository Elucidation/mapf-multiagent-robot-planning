"""Task Status"""
from __future__ import annotations
from enum import Enum


class TaskStatus(Enum):
    """Task Status"""
    OPEN = 'OPEN'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETE = 'COMPLETE'
    ERROR = 'ERROR'
    
    def __str__(self):
        return str(self.value)
