import sqlite3 as sl
from typing import List
import datetime

class DatabaseOrderInserter:
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
                    "destination_id"    INTEGER NOT NULL,
                    "description"   TEXT,
                    "status"   INTEGER,
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
                    FOREIGN KEY("order_id") REFERENCES "Order"("order_id"),
                    FOREIGN KEY("item_id") REFERENCES "Item"("item_id")
                );
                """
            )

    def add_order(self, order: dict):
        order_sql = 'INSERT INTO "Order" (created_by, created, destination_id, description) values(?, ?, ?, ?)'
        order_item_sql = 'INSERT INTO "OrderItem" (order_id, item_id) values(?, ?)'

        self.validate_order(order)
        order_tuple = (
            (
                order["created_by"],
                order["created"],
                order["destination_id"],
                order["description"],
            )
        )

        with self.con:
            c = self.con.cursor()
            c.execute(order_sql, order_tuple)
            order_id = c.lastrowid # Get row_id/primary key id of last insert by this cursor

            order_item_data = []
            for item_id in order["items"]:
                order_item_data.append((order_id, item_id)) # todo get order_id or decide best practice for unique order id
            self.con.executemany(order_item_sql, order_item_data)
            self.con.commit()

    def validate_order(self, order: dict):
        pass  # TODO


if __name__ == "__main__":
    dboi = DatabaseOrderInserter("test2.db")

    # Since we're testing, clear tables first and start fresh
    dboi.reset()

    order = {}
    order["created_by"] = 1
    order["created"] = datetime.datetime.now()
    order["destination_id"] = 3
    order["items"] = [1, 2, 4]
    order["description"] = "orderwith 3 items"

    dboi.add_order(order)
