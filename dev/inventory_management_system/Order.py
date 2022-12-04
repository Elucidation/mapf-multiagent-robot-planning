import sqlite3 as sl
from typing import List
from datetime import datetime
from collections import Counter


class Order:
    def __init__(
        self,
        created_by,
        created,
        description,
        items,
        status="OPEN",
        order_id=None,
        finished=None,
    ):
        self.created_by = created_by
        if type(created) == str:
            self.created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S.%f")
        else:
            self.created = created
        self.description = description
        self.items = Counter(items)
        self.order_id = order_id  # Exists after order added to database
        self.status = status  # status includes OPEN / IN_PROGRESS / FINISHED / ERROR
        if type(finished) == str:
            self.finished = datetime.strptime(finished, "%Y-%m-%d %H:%M:%S.%f")
        else:
            self.finished = finished

    @staticmethod
    def load_from_dict(order_dict: dict):
        return Order(
            order_dict["created_by"],
            order_dict["created"],
            order_dict["description"],
            Counter(order_dict["items"]),
        )

    def validate_order(self):
        # todo : confirm all entries are valid
        pass

    def get_time_to_complete(self):
        if not self.finished:
            return None

        return self.finished - self.created

    def set_open(self):
        self.status = "OPEN"

    def is_open(self):
        return self.status == "OPEN"

    def set_in_progress(self):
        self.status = "IN_PROGRESS"

    def is_in_progress(self):
        return self.status == "IN_PROGRESS"

    def set_complete(self):
        self.status = "COMPLETE"

    def is_complete(self):
        return self.status == "COMPLETE"

    def set_error(self):
        self.status = "ERROR"

    def is_error(self):
        return self.status == "ERROR"

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


class PartialOrder:
    """Tracks a partially filled Order"""

    def __init__(self, order_id: int, items_needed: Counter):
        self.order_id = order_id
        # Counter of item_id : quantity
        self.items_needed = items_needed
        self.items = Counter()

    @staticmethod
    def from_order(order: Order):
        return PartialOrder(order.order_id, Counter(order.items))

    def add_item(self, item_id, quantity=1):
        self.items[item_id] += quantity

    def get_missing_items(self):
        # Counter of item_id : quantity
        # Note, if items > items_needed, it returns 0 still
        # return self.items_needed - self.items
        missing = {}
        for item_id in self.items_needed:
            if item_id in self.items:
                quantity_missing = self.items_needed[item_id] - self.items[item_id]
                if quantity_missing:
                    missing[item_id] = quantity_missing
            else:
                missing[item_id] = self.items_needed[item_id]
        return missing

    def is_complete(self):
        return self.items == self.items_needed

    def __repr__(self):
        if self.is_complete():
            return f"Partial Order for {self.order_id} : {self.items}, Complete"
        return f"Partial Order for {self.order_id} : {self.items}, need {self.get_missing_items()}"


if __name__ == "__main__":
    items_needed = Counter([1, 1, 2])
    p1 = PartialOrder(1, items_needed)
    print(p1.items_needed)
    p1.add_item(1)
    p1.add_item(1)
    p1.add_item(2)
    print(p1.items)
    print(p1.get_missing_items())
    print(p1.is_complete())
