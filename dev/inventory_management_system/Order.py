import sqlite3 as sl
import typing as tp
from typing import List, NewType, Union, Optional
from datetime import datetime
from collections import Counter
from OrderStatus import *
from Item import ItemId, ItemCounter
import Item
OrderId = NewType('OrderId', int)


class Order:
    def __init__(
        self,
        order_id: OrderId,
        items: ItemCounter = ItemCounter(),
        created_by: Optional[int] = None,
        created: Union[str, datetime] = datetime.now(),
        description: str = '',
        status: OrderStatus = OrderStatus.OPEN,
        finished: Union[None, str, datetime] = None,
    ):
        self.created_by = created_by
        
        self.created = created
        if type(created) == str:
            self.created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S.%f")
        
        self.description = description
        self.items = Counter(items)
        self.order_id = order_id  # Exists after order added to database
        self.status = status

        self.finished = finished
        if type(finished) == str:
            self.finished = datetime.strptime(finished, "%Y-%m-%d %H:%M:%S.%f")

    def get_time_to_complete(self):
        if not self.finished:
            return None

        return self.finished - self.created

    def set_open(self):
        self.status = OrderStatus.OPEN

    def is_open(self):
        return self.status == OrderStatus.OPEN

    def set_in_progress(self):
        self.status = OrderStatus.IN_PROGRESS

    def is_in_progress(self):
        return self.status == OrderStatus.IN_PROGRESS

    def set_complete(self):
        self.status = OrderStatus.COMPLETE

    def is_complete(self):
        return self.status == OrderStatus.COMPLETE

    def set_error(self):
        self.status = OrderStatus.ERROR

    def is_error(self):
        return self.status == OrderStatus.ERROR

    def is_finished(self):
        return self.is_complete() or self.is_error()

    def to_json(self):
        return {
            "created_by": self.created_by,
            "created": self.created,
            "description": self.description,
            "items": self.items,
            "status": self.status,
            "order_id": self.order_id,
            "finished": self.finished,
        }

    def __repr__(self):
        return f"Order {self.order_id} [{self.status}]: {self.items}"


if __name__ == "__main__":
    order = Order(description='blah', items=ItemCounter(map(ItemId,[1, 1, 3])), order_id=OrderId(3))
    print(order)
