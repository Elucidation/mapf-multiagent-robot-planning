"""Contains Order class"""
from typing import NewType, Union, Optional
from datetime import datetime
from collections import Counter
from .Item import ItemId, ItemCounter
from .OrderStatus import OrderStatus
OrderId = NewType('OrderId', int)


class Order:
    """Order contains items, status and metadata"""
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
        if isinstance(created, str):
            self.created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S.%f")

        self.description = description
        self.items = Counter(items)
        self.order_id = order_id  # Exists after order added to database
        self.status = status

        self.finished = finished

        if isinstance(finished, str):
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
            "order_id": self.order_id,
            "items": self.items,
            "created_by": self.created_by,
            "created": self.created,
            "description": self.description,
            "status": self.status,
            "finished": self.finished,
        }

    def __repr__(self):
        return f"Order {self.order_id} [{self.status}]: {self.items}"

    def __eq__(self, obj: object) -> bool:
        if isinstance(obj, Order):
            return (
                (self.order_id == obj.order_id) and
                (sorted(self.items.items()) == sorted(obj.items.items())) and
                (self.created_by == obj.created_by) and
                (self.created == obj.created) and
                (self.description == obj.description) and
                (self.status == obj.status) and
                (self.finished == obj.finished)
            )
        else:
            raise NotImplementedError()


if __name__ == "__main__":
    order = Order(description='blah', items=ItemCounter(
        map(ItemId, [1, 1, 3])), order_id=OrderId(3))
    print(order)
