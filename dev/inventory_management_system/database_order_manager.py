import sqlite3 as sl
from typing import List
from datetime import datetime
from Order import *
from Station import *
from collections import Counter


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

    def get_orders(self, N=49999):
        c = self.con.cursor()
        # order_id,created_by,created,finished,description,status
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

    def complete_order(self, order_id):
        sql = """UPDATE "Order" SET finished=?, status="COMPLETE" WHERE order_id=?;"""
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (datetime.now(), order_id))
            self.con.commit()

    def check_stations_finished(self):
        # for each station with a partial order,
        # check if partial order has all items
        # if so, complete that order, delete all partial order items for that order
        # set the completion time
        pass

    def assign_order_to_station(self, order_id, station_id):
        sql = """UPDATE "Station" SET order_id=? WHERE station_id=?;"""
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (order_id, station_id))
            self.con.commit()


    def add_partial_order_items(self, item_list : List[tuple]):
        # item_list = [(order_id, item_id, quantity), ...]
        sql = """INSERT INTO "PartialOrderItem" (order_id, item_id, quantity) VALUES (?, ?, ?);"""

        with self.con:
            c = self.con.cursor()
            self.con.executemany(sql, item_list)
            self.con.commit()

    def get_partial_orders(self):
        c = self.con.cursor()
        #(order_id, item_id, quantity)
        c.execute('SELECT * FROM "PartialOrderItem"')
        # partial_orders = []
        partial_orders = dict()
        for row in c.fetchall():
            (order_id, item_id, quantity) = row
            if order_id not in partial_orders:
                partial_orders[order_id] = PartialOrder(order_id, self.get_items_for_order(order_id))
            partial_orders[order_id].add_item(item_id, quantity)
        return list(partial_orders.values())

    # def get_partial_order(self, partial_order_id):
    #     # Need both OrderItems for items needed
    #     # as well as PartialOrderItems for items currently there
    #     query = """SELECT * FROM "PartialOrder" 
    #                INNER JOIN "OrderItem" ON "OrderItem".order_id = "Order".order_id,
    #                INNER JOIN "PartialOrder" ON "OrderItem".order_id = "Order".order_id,
    #                """
    #     c = self.con.cursor()
    #     c.execute(
    #         'SELECT * FROM "PartialOrder" WHERE partial_order_id=? LIMIT 0, 1',
    #         (partial_order_id,),
    #     )
    #     row = c.fetchone()
    #     if row is None:
    #         return None
    #     return row


if __name__ == "__main__":
    dboi = DatabaseOrderManager("test2.db")

    # Since we're testing, clear tables first and start fresh
    dboi.reset()

    for i in range(3):
        order = Order(
            created_by=1,
            created=datetime.now(),
            items=Counter([1, 2, 2, 4, i]),
            description="order with 3 items",
        )

        dboi.add_order(order)

    orders = dboi.get_orders()
    stations = dboi.get_stations()
    dboi.assign_order_to_station(order_id=orders[0].order_id,station_id=stations[0].station_id)
    stations = dboi.get_stations()
    print(stations)

    # dboi.add_partial_order_items([(1,1,1), (1,2,1), (1,0,1)])
    dboi.add_partial_order_items([(1,1,1), (1,2,2)])
    # dboi.add_partial_order_items([(1,0,1), (1,4,1)])

    dboi.complete_order(orders[2].order_id)
    orders = dboi.get_orders()


    partial_orders = dboi.get_partial_orders()

    print(f'Orders: {orders}')
    print(f'Partial orders: {partial_orders}')

    
