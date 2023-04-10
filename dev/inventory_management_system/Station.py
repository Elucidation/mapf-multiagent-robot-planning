"""Contains Station and Task classes"""
from typing import NewType, Optional
from .Order import OrderId
from .Item import ItemId
from .TaskStatus import TaskStatus
StationId = NewType('StationId', int)
TaskId = NewType('TaskId', int)


class Station():
    """Stations process partial orders"""

    def __init__(self, station_id: StationId, order_id: Optional[OrderId] = None):
        self.station_id = station_id
        self.order_id = order_id

    def assign_order_id(self, order_id: OrderId):
        self.order_id = order_id

    def clear_station(self):
        self.order_id = None

    def has_order(self):
        return self.order_id is not None

    def is_available(self):
        return self.order_id is None

    def __repr__(self):
        if self.is_available():
            return f'Station {self.station_id}: AVAILABLE'
        return f'Station {self.station_id}: Order {self.order_id}'


class Task():
    """Tasks are directives of Item X to Station Y"""

    def __init__(self, task_id: TaskId, station_id: StationId,
                 order_id: OrderId, item_id: ItemId, quantity: int, status: TaskStatus):
        self.task_id = task_id
        self.station_id = station_id
        self.order_id = order_id
        self.item_id = item_id
        self.quantity = quantity
        self.status = status

    def is_complete(self):
        return self.status == TaskStatus.COMPLETE

    def is_error(self):
        return self.status == TaskStatus.ERROR

    def __repr__(self):
        return (f'Task {self.task_id} [{self.status}]: '
                'Item {self.item_id}x{self.quantity} to Station {self.station_id}')
