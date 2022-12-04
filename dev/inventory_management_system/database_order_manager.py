import sqlite3 as sl
from typing import List
from datetime import datetime
from Order import *
from Station import *
from collections import Counter
import time


class DatabaseOrderManager:
    """DB Manager for Order interactions"""

    def __init__(self, db_filename):
        self.con = sl.connect(db_filename)

        self.init_tables()

    def reset(self):
        self.delete_tables()
        self.init_tables()
        self.init_stations()

    def delete_tables(self):
        self.con.executescript(
            """
            DROP TABLE "Order";
            DROP TABLE "Item";
            DROP TABLE "OrderItem";
            DROP TABLE "PartialOrderItem";
            DROP TABLE "Station";
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
                CREATE TABLE IF NOT EXISTS "PartialOrderItem" (
                    "order_id"  INTEGER NOT NULL,
                    "item_id"  INTEGER NOT NULL,
                    "quantity"  INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY("order_id", "item_id"),
                    FOREIGN KEY("order_id") REFERENCES "Order"("order_id"),
                    FOREIGN KEY("item_id") REFERENCES "Item"("item_id")
                );
                CREATE TABLE IF NOT EXISTS "Station" (
                    "station_id"  INTEGER NOT NULL UNIQUE,
                    "order_id"  INTEGER,
                    PRIMARY KEY("station_id"),
                    FOREIGN KEY("order_id") REFERENCES "Order"("order_id")
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

    def init_stations(self):
        self.add_station()
        self.add_station()
    
    def add_station(self):
        sql = 'INSERT INTO "Station" DEFAULT VALUES;'
        with self.con:
            c = self.con.cursor()
            c.execute(sql)
            self.con.commit()

    def add_order(self, order: Order):
        order.validate_order()
        order_sql = 'INSERT INTO "Order" (created_by, created, description, status) values(?, ?, ?, ?)'
        order_item_sql = (
            'INSERT INTO "OrderItem" (order_id, item_id, quantity) values(?, ?, ?)'
        )
        with self.con:
            c = self.con.cursor()
            c.execute(order_sql, self.get_db_order_tuple(order))
            # Get row_id/primary key id of last insert by this cursor
            order_id = c.lastrowid
            self.con.executemany(
                order_item_sql, self.get_db_order_items_tuples(order, order_id)
            )
            self.con.commit()

    def get_orders(self, N=49999, status=None):
        c = self.con.cursor()
        # order_id,created_by,created,finished,description,status
        if status:
            c.execute('SELECT * FROM "Order" WHERE status=? LIMIT 0, ?', (status, N))
        else:
            c.execute('SELECT * FROM "Order" LIMIT 0, ?', (N,))
        orders = []
        while True:
            row = c.fetchone()
            if row is None:
                break

            (order_id, created_by, created, finished, description, status) = row
            items = self.get_items_for_order(order_id)
            order = Order(
                order_id=order_id,
                created_by=created_by,
                created=created,
                finished=finished,
                description=description,
                status=status,
                items=items,
            )
            orders.append(order)
        return orders

    def get_items_for_order(self, order_id):
        c = self.con.cursor()

        c.execute('SELECT * FROM "OrderItem" WHERE order_id=?', (order_id,))
        # list of (order_id, item_id, quantity)
        items = Counter()
        for row in c.fetchall():
            items[row[1]] += row[2]
        return items

    def get_stations(self, N=49999):
        c = self.con.cursor()
        # A limited number of stations, so get them all at once
        # station_id,partial_order_id
        c.execute('SELECT * FROM "Station" LIMIT 0, ?', (N,))
        stations = []
        for row in c.fetchall():
            (station_id, order_id) = row
            station = Station(station_id, order_id)
            stations.append(station)
        return stations

    def set_order_status(self, order_id, status):
        sql = """UPDATE "Order" SET finished=?, status=? WHERE order_id=?;"""
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (datetime.now(), status, order_id))
            self.con.commit()

    def set_order_in_progress(self, order_id):
        self.set_order_status(order_id, "IN_PROGRESS")

    def complete_order(self, order_id):
        self.set_order_status(order_id, "COMPLETE")
        self.clear_partial_order_items(order_id)

    def clear_partial_order_items(self, order_id):
        # Remove partial items associated with a given order
        sql = """DELETE FROM "PartialOrderItem" WHERE order_id=?;"""
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (order_id, ))
            self.con.commit()

    def update_stations(self):
        # for each station with a partial order,
        # check if partial order has all items
        # if so, complete that order, delete all partial order items for that order
        # set the completion time
        stations = self.get_stations()
        stations_by_partial_order_id = {station.order_id : station for station in stations if station.order_id is not None}
        partial_orders = self.get_partial_orders()
        for partial_order in partial_orders:
            if partial_order.is_complete():
                station = stations_by_partial_order_id[partial_order.order_id]
                print(f'Finished {station}')
                # Make station available
                self.clear_station(station.station_id)
                self.complete_order(partial_order.order_id)


    def clear_station(self, station_id):
        self.assign_order_to_station(None, station_id)

    def assign_order_to_station(self, order_id, station_id):
        sql = """UPDATE "Station" SET order_id=? WHERE station_id=?;"""
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (order_id, station_id))
            self.con.commit()
        self.set_order_in_progress(order_id)

    def update_partial_order_item_quantity(self, order_id, item_id, quantity):
        sql = """UPDATE "PartialOrderItem" SET quantity=? WHERE order_id=? AND item_id=?;"""
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (quantity, order_id, item_id))
            self.con.commit()

    def add_item_to_partial_order(self, order_id, item_id, quantity=1):
        # 
        sql = """SELECT quantity FROM "PartialOrderItem" WHERE order_id=? AND item_id=?;"""
        new_quantity = quantity
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (order_id, item_id))
            row = c.fetchone()
            if row is None:
                self.set_partial_order_items([(order_id, item_id, quantity)])
            else:
                self.update_partial_order_item_quantity(order_id, item_id, quantity + row[0])

        self.update_stations()


    def set_partial_order_items(self, item_list : List[tuple]):
        # NOTE: Currently overwrites
        # item_list = [(order_id, item_id, quantity), ...]
        sql = """INSERT INTO "PartialOrderItem" (order_id, item_id, quantity) VALUES (?, ?, ?);"""

        with self.con:
            c = self.con.cursor()
            self.con.executemany(sql, item_list)
            self.con.commit()

    def get_partial_orders(self):
        # Expect all partial order items to be for orders with status IN_PROGRESS
        in_progress_orders = self.get_orders(status="IN_PROGRESS")
        partial_orders = dict()
        for order in in_progress_orders:
            order_id = order.order_id
            partial_orders[order_id] = PartialOrder(order_id, self.get_items_for_order(order_id))

        c = self.con.cursor()
        #(order_id, item_id, quantity)
        c.execute('SELECT * FROM "PartialOrderItem"')
        for row in c.fetchall():
            (order_id, item_id, quantity) = row
            partial_orders[order_id].add_item(item_id, quantity)
        return list(partial_orders.values())


if __name__ == "__main__":
    dboi = DatabaseOrderManager("test2.db")

    # Since we're testing, clear tables first and start fresh
    dboi.reset()

    # time.sleep(1)

    for i in range(3):
        order = Order(
            created_by=1,
            created=datetime.now(),
            items=Counter([1, 2, 2, 4, i]),
            description="order with 5 items",
        )

        dboi.add_order(order)
        # time.sleep(1)

    orders = dboi.get_orders()
    stations = dboi.get_stations()
    # time.sleep(1)
    dboi.assign_order_to_station(order_id=1,station_id=1)
    # time.sleep(1)
    dboi.assign_order_to_station(order_id=3, station_id=2)
    # time.sleep(1)
    stations = dboi.get_stations()
    print(f'Orders: {orders}')
    print(f'Stations: {stations}')

    # time.sleep(1)
    dboi.add_item_to_partial_order(order_id=1, item_id=0, quantity=1)
    # time.sleep(1)
    dboi.add_item_to_partial_order(order_id=1, item_id=1, quantity=1)
    # time.sleep(1)
    dboi.add_item_to_partial_order(order_id=1, item_id=2, quantity=2)
    # time.sleep(1)
    dboi.add_item_to_partial_order(order_id=1, item_id=4, quantity=1)
    # time.sleep(1)
    

    # dboi.set_partial_order_items([(3,2,1), (3,4,1)])
    dboi.add_item_to_partial_order(order_id=3, item_id=2, quantity=1)
    # time.sleep(1)
    dboi.add_item_to_partial_order(order_id=3, item_id=2, quantity=1)
    # time.sleep(1)

    # dboi.complete_order(orders[2].order_id)
    orders = dboi.get_orders()
    stations = dboi.get_stations()


    partial_orders = dboi.get_partial_orders()
    # complete_orders = [order for order in orders if order.status == "COMPLETE"]

    print('-----')
    print(f'Orders: {orders}')
    print(f'Stations: {stations}')
    print(f'Partial orders: {partial_orders}')
    # print(f'Complete orders: {complete_orders}')

    
