import sqlite3 as sl
from typing import List
import datetime
from Order import Order
from collections import Counter


class DatabaseOrderInserter:
    order_sql = 'INSERT INTO "Order" (created_by, created, description, status) values(?, ?, ?, ?)'
    order_item_sql = 'INSERT INTO "OrderItem" (order_id, item_id, quantity) values(?, ?, ?)'
    """docstring for DatabaseOrderInserter"""

    def __init__(self, db_filename):
        self.con = sl.connect(db_filename)

        self.init_tables()

    def reset(self):
        self.delete_tables()
        self.init_tables()

    def delete_tables(self):
        self.con.executescript(
            """
            DROP TABLE "Order";
            DROP TABLE "Item";
            DROP TABLE "OrderItem";
            """
        )

    def init_tables(self):
        with self.con:
            self.con.executescript(
                """
                CREATE TABLE IF NOT EXISTS "Order" (
                    "order_id"  INTEGER NOT NULL UNIQUE,
                    "created_by"    INTEGER NOT NULL,
                    "created" INTEGER NOT NULL,
                    "finished" INTEGER,
                    "description"   TEXT,
                    "status"   TEXT,
                    PRIMARY KEY("order_id")
                );
                CREATE TABLE IF NOT EXISTS "Item" (
                    "item_id"  INTEGER NOT NULL UNIQUE,
                    "name"   TEXT NOT NULL,
                    "description"   TEXT,
                    "color"   TEXT,
                    PRIMARY KEY("item_id")
                );
                CREATE TABLE IF NOT EXISTS "OrderItem" (
                    "order_id"  INTEGER NOT NULL,
                    "item_id"  INTEGER NOT NULL,
                    "quantity"  INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY("order_id", "item_id"),
                    FOREIGN KEY("order_id") REFERENCES "Order"("order_id"),
                    FOREIGN KEY("item_id") REFERENCES "Item"("item_id")
                );
                """
            )

    @staticmethod
    def get_db_order_tuple(order: Order):
        order_tuple = (
            order.created_by,
            order.created,
            order.description,
            order.status,
        )
        return order_tuple

    @staticmethod
    def get_db_order_items_tuples(order: Order, order_id):
        order.order_id = order_id  # Update order_id
        order_item_data = []
        for item_id, quantity in order.items.items():
            order_item_data.append((order_id, item_id, quantity))
        return order_item_data

    def add_order(self, order: Order):
        order.validate_order()
        with self.con:
            c = self.con.cursor()
            c.execute(self.order_sql, self.get_db_order_tuple(order))
            # Get row_id/primary key id of last insert by this cursor
            order_id = c.lastrowid
            self.con.executemany(
                self.order_item_sql, self.get_db_order_items_tuples(order, order_id)
            )
            self.con.commit()


if __name__ == "__main__":
    dboi = DatabaseOrderInserter("test2.db")

    # Since we're testing, clear tables first and start fresh
    dboi.reset()

    order = Order(
        created_by=1,
        created=datetime.datetime.now(),
        items=Counter([1, 2, 2, 4]),
        description="order with 3 items",
    )

    dboi.add_order(order)