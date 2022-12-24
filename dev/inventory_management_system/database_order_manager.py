import sqlite3 as sl
from typing import List, Tuple, cast
import typing
from datetime import datetime
from Order import *
from Station import *
from TaskStatus import TaskStatus
from Item import ItemId
import Item
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
            DROP TABLE "Station";
            DROP TABLE "Task";
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
                CREATE TABLE IF NOT EXISTS "Station" (
                    "station_id"  INTEGER NOT NULL UNIQUE,
                    "order_id"  INTEGER,
                    PRIMARY KEY("station_id"),
                    FOREIGN KEY("order_id") REFERENCES "Order"("order_id")
                );
                CREATE TABLE IF NOT EXISTS "Task" (
                    "station_id"  INTEGER NOT NULL,
                    "order_id"  INTEGER NOT NULL,
                    "item_id"  INTEGER NOT NULL,
                    "quantity"  INTEGER NOT NULL,
                    "status"   TEXT,
                    PRIMARY KEY("station_id", "order_id", "item_id"),
                    FOREIGN KEY("station_id") REFERENCES "Station"("station_id"),
                    FOREIGN KEY("order_id") REFERENCES "Order"("order_id")
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
    def get_db_order_items_tuples(order_id: OrderId, items: ItemCounter):
        order_item_data = []
        for item_id, quantity in items.items():
            order_item_data.append((order_id, item_id, quantity))
        return order_item_data

    def init_stations(self):
        self.add_station()
        self.add_station()
        self.add_station()

    def add_station(self):
        sql = 'INSERT INTO "Station" DEFAULT VALUES;'
        with self.con:
            c = self.con.cursor()
            c.execute(sql)
            self.con.commit()

    # TODO: type params
    def add_order(self, items: ItemCounter, created_by: int, created: datetime, description: str, status: OrderStatus = OrderStatus.OPEN):
        order_sql = 'INSERT INTO "Order" (created_by, created, description, status) values(?, ?, ?, ?)'
        order_item_sql = (
            'INSERT INTO "OrderItem" (order_id, item_id, quantity) values(?, ?, ?)'
        )
        with self.con:
            c = self.con.cursor()
            c.execute(order_sql, (created_by, created,
                      description, str(status)))
            # Get row_id/primary key id of last insert by this cursor
            order_id = OrderId(c.lastrowid)
            self.con.executemany(
                order_item_sql, self.get_db_order_items_tuples(order_id, items)
            )
            self.con.commit()
        return Order(
            order_id=order_id,
            created_by=created_by,
            created=created,
            description=description,
            items=items,
        )

    def get_orders(self, N=49999, status=None):
        c = self.con.cursor()
        # order_id,created_by,created,finished,description,status
        if status:
            c.execute(
                'SELECT * FROM "Order" WHERE status=? LIMIT 0, ?', (status, N))
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
                order_id=OrderId(order_id),
                created_by=created_by,
                created=created,
                finished=finished,
                description=description,
                status=OrderStatus(status),
                items=items,
            )
            orders.append(order)
        return orders

    def get_items_for_order(self, order_id: int) -> ItemCounter:
        """Returns Counter of {item_id : quantity} """
        c = self.con.cursor()
        c.execute(
            'SELECT order_id, item_id, quantity FROM "OrderItem" WHERE order_id=?', (order_id,))
        items: Counter = Counter()
        for _, item_id, quantity in c.fetchall():
            items[ItemId(item_id)] += quantity
        return items

    def get_available_stations(self, N=49999):
        c = self.con.cursor()
        # Find stations with unset order_id (ie. available)
        c.execute(
            'SELECT * FROM "Station" WHERE order_id IS ? LIMIT 0, ?', (None, N))
        stations = []
        for row in c.fetchall():
            (station_id, order_id) = row
            station = Station(station_id, order_id)
            stations.append(station)

        return stations

    def get_stations(self, N: int = 49999) -> List[Station]:
        c = self.con.cursor()
        # A limited number of stations, so get them all at once
        c.execute('SELECT station_id, order_id FROM "Station" LIMIT 0, ?', (N,))
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

    def update_station(self, station_id: StationId):
        """Check if station has any uncomplete tasks. 
        If all tasks are complete, complete the station order"""
        tasks = self.get_station_tasks(station_id=station_id)
        for task in tasks:
            if task.status != TaskStatus.COMPLETE:
                return
        order_id = self.get_station_order(station_id)
        self.complete_order(order_id)
        self.clear_station(station_id)

    def clear_station(self, station_id):
        self.assign_order_to_station(None, station_id)

    def assign_order_to_station(self, order_id: OrderId, station_id: StationId):
        """Assign order to station, and add all tasks of items to station"""
        station_curr_order = self.get_station_order(station_id)
        if order_id != None and station_curr_order != None:
            print(
                f"Station {station_id} already has an order {station_curr_order}, not assigning order {order_id}")
            return False
        
        # Add tasks for moving items in order to that station
        tasks = []
        status = 'OPEN'
        for item_id, quantity in self.get_items_for_order(order_id).items():
            tasks.append((station_id, order_id, item_id, quantity, status))
        
        sql = """UPDATE "Station" SET order_id=? WHERE station_id=?;"""
        tasks_sql = (
            'INSERT INTO "Task" (station_id, order_id, item_id, quantity, status) values(?, ?, ?, ?, ?)'
        )
        
        with self.con:
            c = self.con.cursor()
            # Assign order to station
            c.execute(sql, (order_id, station_id))
            # Add tasks for items->station for that order
            c.executemany(tasks_sql, tasks)
            self.con.commit()

        self.set_order_in_progress(order_id)
        return True

    def get_station_order(self, station_id):
        # Returns order ID assigned to station or None if station is empty/available
        c = self.con.cursor()
        c.execute(
            'SELECT order_id FROM "Station" WHERE station_id=?', (station_id,))
        row = c.fetchone()
        if row is None:
            return None
        return row[0]  # order_id

    def get_station_with_order_id(self, order_id):
        # Returns station ID assigned to station or None if station is empty/available
        c = self.con.cursor()
        c.execute('SELECT station_id FROM "Station" WHERE order_id=?', (order_id,))
        row = c.fetchone()
        if row is None:
            return None
        return row[0]  # station_id

    def add_item_to_station(self, station_id: StationId, item_id: ItemId, quantity=1) -> bool:
        """Updates or Completes Task for adding items to a station.
        Returns bool on success or failure"""
        sql = """SELECT quantity, status FROM "Task" WHERE station_id=? AND item_id=? AND (status='OPEN' OR status='IN_PROGRESS');"""
        new_quantity = quantity
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (station_id, item_id))
            row = c.fetchone()
            if row is None:
                print(
                    f'Task {item_id} -> station {station_id} not found, ignoring')
                return False
            task_quantity, task_status = row
            new_quantity = task_quantity - quantity
            if new_quantity == 0:
                # Finish task since all items moved
                new_status = 'COMPLETE'
            elif new_quantity < 0:
                # Error task since too many items moved
                new_status = 'ERROR'
            else:
                # Make task available again
                new_status = 'OPEN'
        self.update_task(station_id, item_id, new_quantity, new_status)
        self.update_station(station_id)
        return True

    def update_task(self, station_id: int, item_id: int, quantity: int, status: str):
        sql = """UPDATE "Task" SET quantity=?, status=? WHERE station_id=? AND item_id=? AND (status='OPEN' OR status='IN_PROGRESS');"""
        with self.con:
            c = self.con.cursor()
            c.execute(sql, (quantity, status, station_id, item_id))
            self.con.commit()

    def get_stations_and_tasks(self) -> List[Tuple[Station, List[Task]]]:
        stations = self.get_stations()
        station_tasks = []
        for station in stations:
            tasks = self.get_station_tasks(station.station_id)
            station_tasks.append((station, tasks))
        return station_tasks

    def get_station_tasks(self, station_id: int, N=49999) -> List[Task]:
        c = self.con.cursor()
        c.execute(
            'SELECT station_id, order_id, item_id, quantity, status FROM "Task" WHERE station_id=? LIMIT 0, ?', (station_id, N))
        tasks = []
        for row in c.fetchall():
            (station_id, order_id, item_id, quantity, status) = row
            task = Task(station_id=StationId(station_id), order_id=OrderId(order_id), item_id=ItemId(item_id),
                        quantity=quantity, status=TaskStatus(status))
            tasks.append(task)
        return tasks

    def get_tasks(self, query_status: Optional[TaskStatus] = None, N=49999) -> List[Task]:
        c = self.con.cursor()
        if query_status:
            c.execute(
                'SELECT station_id, order_id, item_id, quantity, status FROM "Task" WHERE status=? LIMIT 0, ?', (str(query_status), N))
        else:
            c.execute(
                'SELECT station_id, order_id, item_id, quantity, status FROM "Task" LIMIT 0, ?', (N,))

        tasks = []
        for row in c.fetchall():
            (station_id, order_id, item_id, quantity, status) = row
            task = Task(StationId(station_id), OrderId(order_id),
                        ItemId(item_id), quantity, TaskStatus(status))
            tasks.append(task)
        return tasks


if __name__ == "__main__":
    dboi = DatabaseOrderManager("test2.db")

    # Since we're testing, clear tables first and start fresh
    dboi.reset()

    # time.sleep(1)

    for i in range(3):
        order = dboi.add_order(created_by=1,
                               created=datetime.now(),
                               items=Item.make_counter_of_items(
                                   [1, 2, 2, 4, i]),
                               description="order with 5 items")
        # time.sleep(1)

    orders = dboi.get_orders()
    stations = dboi.get_stations()
    # time.sleep(1)
    dboi.assign_order_to_station(OrderId(1), StationId(1))
    # time.sleep(1)
    dboi.assign_order_to_station(OrderId(3), StationId(2))
    # time.sleep(1)
    stations = dboi.get_stations()
    print('----')
    print(f'Orders: {orders}')
    print(f'Stations: {stations}')
    print('----')

    # time.sleep(1)
    dboi.add_item_to_station(StationId(1), ItemId(0), quantity=1)
    # time.sleep(1)
    dboi.add_item_to_station(StationId(1), ItemId(1), quantity=1)
    # time.sleep(1)
    dboi.add_item_to_station(StationId(1), ItemId(2), quantity=2)
    # time.sleep(1)
    dboi.add_item_to_station(StationId(1), ItemId(4), quantity=1)
    # time.sleep(1)

    dboi.add_item_to_station(StationId(2), ItemId(2), quantity=1)
    # time.sleep(1)
    dboi.add_item_to_station(StationId(2), ItemId(2), quantity=1)
    # dboi.add_item_to_station(StationId(2), ItemId(2), quantity=1)
    # dboi.add_item_to_station(StationId(2), ItemId(1), quantity=1)
    # dboi.add_item_to_station(StationId(2), ItemId(4), quantity=1)
    # time.sleep(1)

    # dboi.complete_order(orders[2].order_id)
    orders = dboi.get_orders()
    stations = dboi.get_stations()

    tasks = dboi.get_tasks()
    incomplete_tasks = [task for task in tasks if task.status != 'COMPLETE']
    # complete_orders = [order for order in orders if order.status == "COMPLETE"]

    print('-----')
    print(f'Orders: {orders}')
    print(f'Stations: {stations}')
    print(f'Tasks: {tasks}')
    print(f'Incomplete Tasks: {incomplete_tasks}')
    print('-----')
    # print(f'Complete orders: {complete_orders}')
