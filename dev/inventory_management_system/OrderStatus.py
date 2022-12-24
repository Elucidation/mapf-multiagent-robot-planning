from __future__ import annotations
from enum import Enum


class OrderStatus(Enum):
    OPEN = 'OPEN'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETE = 'COMPLETE'
    ERROR = 'ERROR'

    @staticmethod
    def load(value: str) -> OrderStatus:
        if value == OrderStatus.OPEN:
            return OrderStatus.OPEN
        elif value == OrderStatus.IN_PROGRESS:
            return OrderStatus.IN_PROGRESS
        elif value == OrderStatus.COMPLETE:
            return OrderStatus.COMPLETE

        return OrderStatus.ERROR
    
    def __str__(self):
        return str(self.value)
