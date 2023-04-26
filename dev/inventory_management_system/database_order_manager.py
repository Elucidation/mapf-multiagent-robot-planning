"""Order Manager DB contains Orders/Items/Stations/Tasks and their relationships"""
import functools
import sqlite3 as sl
import time
from typing import List, Optional, Tuple
from datetime import datetime
import logging
from collections import Counter

from .Order import Order, OrderId
from .OrderStatus import OrderStatus
from .Station import Station, StationId, Task, TaskId
from .TaskStatus import TaskStatus
from .Item import ItemCounter, ItemId, get_item_names
# pylint: disable=C0301:line-too-long

MAIN_DB = "./inventory_management_system/orders.db"

# Set up logging
logger = logging.getLogger("database_order_manager")


def timeit(func):
    """Decorator for timing functions in WDB"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f'{func.__name__!r} Start')
        t_start = time.perf_counter()
        result = func(*args, **kwargs)
        t_end = time.perf_counter()
        logger.debug(
            f'{func.__name__!r} End. Took {(t_end - t_start)*1000:.3f} ms')
        return result
    return wrapper


class DatabaseOrderManager:
    """Manager for interacting with the Order/Station/Item/Task database"""

    def __init__(self, db_filename):
        self.con = sl.connect(db_filename)
        logger.debug(f'DatabaseOrderManager DB connected to {db_filename}')

    def reset(self):
        self.delete_tables()
        self.init_tables()
        self.init_stations()
        self.init_items()

    def delete_tables(self):
        self.con.executescript(
            """
            DROP TABLE IF EXISTS "Order";
            DROP TABLE IF EXISTS "Item";
            DROP TABLE IF EXISTS "OrderItem";
            DROP TABLE IF EXISTS "Station";
            DROP TABLE IF EXISTS "Task";
            """
        )
        self.con.commit()

    def init_tables(self):
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
                PRIMARY KEY("station_id" AUTOINCREMENT),
                FOREIGN KEY("order_id") REFERENCES "Order"("order_id")
            );
            CREATE TABLE IF NOT EXISTS "Task" (
                "task_id" INTEGER NOT NULL,
                "station_id"  INTEGER NOT NULL,
                "order_id"  INTEGER NOT NULL,
                "item_id"  INTEGER NOT NULL,
                "quantity"  INTEGER NOT NULL,
                "status"   TEXT,
                PRIMARY KEY("task_id" AUTOINCREMENT),
                FOREIGN KEY("station_id") REFERENCES "Station"("station_id"),
                FOREIGN KEY("order_id") REFERENCES "Order"("order_id")
                FOREIGN KEY("item_id") REFERENCES "Item"("item_id")
            );""")
        self.con.commit()

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
        self.add_station()
        self.add_station()  # TODO : Hacky amount

    def init_items(self):
        item_names = get_item_names()
        item_sql = 'INSERT INTO "Item" (name) values(?)'
        item_name_data = list(map(lambda item_name: (item_name,), item_names))
        with self.con:
            self.con.executemany(item_sql, item_name_data)

    def add_station(self):
        sql = 'INSERT INTO "Station" DEFAULT VALUES;'
        with self.con:
            self.con.execute(sql)

    @timeit
    def add_order(self, items: ItemCounter, created_by: int,
                  created: Optional[datetime] = None, description: str = "",
                  status: OrderStatus = OrderStatus.OPEN) -> Order:
        """Add a new order to the database.

        Args:
            items (ItemCounter): Counter of Item ids
            created_by (int): User id (todo: unused)
            created (datetime, optional): Creation date. Defaults to now.
            description (str, optional): Order description. Defaults to "".
            status (OrderStatus, optional): Order status. Defaults to OrderStatus.OPEN.

        Returns:
            bool: Success or failure to add new order
        """
        order_sql = (
            'INSERT INTO "Order" (created_by, created, description, status) values(?, ?, ?, ?)')
        order_item_sql = (
            'INSERT INTO "OrderItem" (order_id, item_id, quantity) values(?, ?, ?)'
        )
        if created is None:
            created = datetime.now()  # Use current time if none provided.
        with self.con:
            cur = self.con.cursor()
            cur.execute(order_sql, (created_by, created,
                                    description, str(status)))
            # Get row_id/primary key id of last insert by this cursor
            order_id = OrderId(cur.lastrowid)
            self.con.executemany(
                order_item_sql, self.get_db_order_items_tuples(order_id, items)
            )
        return Order(
            order_id=order_id,
            created_by=created_by,
            created=created,
            description=description,
            items=items,
        )

    @timeit
    def get_orders(self, limit_rows: int = 49999, status=None) -> List[Order]:
        cur = self.con.cursor()
        # order_id,created_by,created,finished,description,status
        if status:
            cur.execute(
                'SELECT * FROM "Order" WHERE status=? LIMIT ?', (status, limit_rows))
        else:
            cur.execute('SELECT * FROM "Order" LIMIT ?', (limit_rows,))
        orders = []
        while True:
            row = cur.fetchone()
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

    @timeit
    def get_items_for_order(self, order_id: int) -> ItemCounter:
        """Returns Counter of {item_id : quantity} """
        result = self.con.execute(
            'SELECT order_id, item_id, quantity FROM "OrderItem" WHERE order_id=?', (order_id,))
        items: Counter = Counter()
        for _, item_id, quantity in result:
            items[ItemId(item_id)] += quantity
        return items

    @timeit
    def get_available_stations(self, limit_rows=49999):
        # Find stations with unset order_id (ie. available)
        result = self.con.execute(
            'SELECT * FROM "Station" WHERE order_id IS ? LIMIT ?', (None, limit_rows))
        stations = []
        for row in result:
            (station_id, order_id) = row
            station = Station(station_id, order_id)
            stations.append(station)

        return stations

    @timeit
    def get_station(self, station_id: StationId) -> Optional[Station]:
        # Get station by id if it exists.
        result = self.con.execute(
            'SELECT station_id, order_id FROM "Station" WHERE station_id = ? LIMIT 1', (station_id,))
        row = result.fetchone()
        if not row:
            return None
        (station_id, order_id) = row
        return Station(station_id, order_id)

    @timeit
    def get_stations(self, limit_rows: int = 49999) -> List[Station]:
        # A limited number of stations, so get them all at once
        result = self.con.execute(
            'SELECT station_id, order_id FROM "Station" LIMIT ?', (limit_rows,))
        stations = []
        for row in result:
            (station_id, order_id) = row
            station = Station(station_id, order_id)
            stations.append(station)
        return stations

    @timeit
    def set_order_status(self, order_id, status):
        sql = """UPDATE "Order" SET finished=?, status=? WHERE order_id=?;"""
        with self.con:
            self.con.execute(sql, (datetime.now(), status, order_id))

    def set_order_in_progress(self, order_id):
        self.set_order_status(order_id, "IN_PROGRESS")

    def complete_order(self, order_id):
        self.set_order_status(order_id, "COMPLETE")

    def _update_station(self, station_id: StationId) -> bool:
        """Check if station has any uncomplete tasks. 
        If all tasks are complete, complete the station order
        returns bool if station is cleared"""
        tasks = self.get_incomplete_station_tasks(station_id=station_id)
        if tasks:
            return False
        order_id = self.get_station_order(station_id)
        self.complete_order(order_id)
        self.clear_station(station_id)
        return True

    def clear_station(self, station_id: StationId):
        self.assign_order_to_station(None, station_id)

    @timeit
    def assign_order_to_station(self, order_id: Optional[OrderId], station_id: StationId) -> bool:
        """Assign an order to a station, and add all tasks of items to station. 

        Args:
            order_id (OrderId): The ID of the order to be assigned, or None if empty.
            station_id (StationId): The ID of the station to assign the order to.

        Returns:
            bool: success or failure
        """
        station_curr_order = self.get_station_order(station_id)
        if (order_id is not None) and (station_curr_order is not None):
            logger.info(
                f"Station {station_id} already has an order {station_curr_order}, not assigning order {order_id}")
            return False

        # Add tasks for moving items in order to that station
        tasks = []
        status = TaskStatus.OPEN
        if order_id:
            for item_id, quantity in self.get_items_for_order(order_id).items():
                tasks.append(
                    (station_id, order_id, item_id, quantity, str(status)))

        sql = """UPDATE "Station" SET order_id=? WHERE station_id=?;"""
        tasks_sql = (
            'INSERT INTO "Task" (station_id, order_id, item_id, quantity, status) values(?, ?, ?, ?, ?)'
        )

        with self.con:
            # Assign order to station
            self.con.execute(sql, (order_id, station_id))
            # Add tasks for items->station for that order
            self.con.executemany(tasks_sql, tasks)

        self.set_order_in_progress(order_id)
        return True

    @timeit
    def get_station_order(self, station_id: StationId) -> Optional[OrderId]:
        # Returns order ID assigned to station or None if station is empty/available
        result = self.con.execute(
            'SELECT order_id FROM "Station" WHERE station_id=? LIMIT 1', (station_id,))
        row = result.fetchone()
        if not row:
            return None
        return row[0]  # order_id

    @timeit
    def get_station_with_order_id(self, order_id: OrderId) -> Optional[StationId]:
        # Returns station ID assigned to station or None if station is empty/available
        result = self.con.execute(
            'SELECT station_id FROM "Station" WHERE order_id=?', (order_id,))
        row = result.fetchone()
        if not row:
            return None
        return row[0]  # station_id

    @timeit
    def add_item_to_station(self, station_id: StationId, item_id: ItemId, quantity=1) -> bool:
        """Add items to a station: Updates or Completes Task and Station associated.

        Args:
            station_id (StationId): The ID of the station to add the items to.
            item_id (ItemId): The ID of the item to be added.
            quantity (int): The number of items to be added.

        Returns:
            bool: success or failure
        """
        sql = """SELECT quantity FROM "Task" WHERE station_id=? AND item_id=? AND (status='OPEN' OR status='IN_PROGRESS');"""
        new_quantity = quantity
        result = self.con.execute(sql, (station_id, item_id))
        row = result.fetchone()
        if row is None:
            logger.info(
                f'Task {item_id} -> station {station_id} not found, ignoring')
            return False
        current_quantity = row[0]
        new_quantity = current_quantity - quantity
        if new_quantity == 0:
            # Finish task since all items moved
            new_status = TaskStatus.COMPLETE
        elif new_quantity < 0:
            # Error task since too many items moved
            new_status = TaskStatus.ERROR
        else:
            # Make task available again
            new_status = TaskStatus.OPEN
        self.update_related_task(station_id, item_id, new_quantity, new_status)
        if new_status == TaskStatus.COMPLETE:
            # Check if station has any tasks left or update if it's complete
            self._update_station(station_id)
        return True

    @timeit
    def update_related_task(self, station_id: StationId, item_id: ItemId, quantity: int, status: TaskStatus):
        """Updates task with new quantity and status."""
        sql = """UPDATE "Task" SET quantity=?, status=? WHERE station_id=? AND item_id=? AND (status='OPEN' OR status='IN_PROGRESS');"""
        with self.con:
            self.con.execute(
                sql, (quantity, status.value, station_id, item_id))

    @timeit
    def update_task_status(self, task_id: TaskId, status: TaskStatus):
        """Updates task with new quantity and status."""
        sql = """UPDATE "Task" SET status=? WHERE task_id=?;"""
        with self.con:
            self.con.execute(sql, (status.value, task_id))

    @timeit
    def get_stations_and_tasks(self) -> List[Tuple[Station, List[Task]]]:
        stations = self.get_stations()
        station_tasks = []
        for station in stations:
            tasks = self.get_incomplete_station_tasks(station.station_id)
            station_tasks.append((station, tasks))
        return station_tasks

    @timeit
    def get_incomplete_station_tasks(self, station_id: int, limit_rows=49999) -> List[Task]:
        """Return incomplete tasks associated with a station"""
        result = self.con.execute(
            'SELECT task_id, station_id, order_id, item_id, quantity, status FROM "Task" WHERE station_id=? LIMIT ?', (station_id, limit_rows))
        tasks = []
        for row in result:
            (task_id, station_id, order_id, item_id, quantity, status) = row
            task = Task(TaskId(task_id), station_id=StationId(station_id), order_id=OrderId(order_id), item_id=ItemId(item_id),
                        quantity=quantity, status=TaskStatus(status))
            if not task.is_complete():
                tasks.append(task)
        return tasks

    @timeit
    def get_tasks(self, query_status: Optional[TaskStatus] = None, limit_rows=49999) -> List[Task]:
        if query_status:
            sql = 'SELECT task_id, station_id, order_id, item_id, quantity, status FROM "Task" WHERE status=? LIMIT ?'
            vals = [str(query_status), limit_rows]
        else:
            sql = 'SELECT task_id, station_id, order_id, item_id, quantity, status FROM "Task" LIMIT ?'
            vals = [limit_rows]
        result = self.con.execute(sql, vals)

        tasks = []
        for row in result:
            (task_id, station_id, order_id, item_id, quantity, status) = row
            task = Task(TaskId(task_id), StationId(station_id), OrderId(order_id),
                        ItemId(item_id), quantity, TaskStatus(status))
            tasks.append(task)
        return tasks

    @timeit
    def fill_available_station(self) -> bool:
        """Adds an open order to an available station if they both exist.

        Returns:
            bool: Whether an order was assigned to a station
        """
        stations = self.get_available_stations(limit_rows=1)
        if len(stations) == 0:
            return False
        orders = self.get_orders(limit_rows=1, status='OPEN')
        if len(orders) == 0:
            return False
        self.assign_order_to_station(
            order_id=orders[0].order_id, station_id=stations[0].station_id)
        logger.info(f'Filled {stations[0]} with {orders[0]}')
        return True
