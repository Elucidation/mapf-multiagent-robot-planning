"""Basic test creation of a Database, assign orders, add items, check incomplete tasks etc."""

# from dev dir, run `python -m unittest inventory_management_system.test_database_order_manager`
import unittest
from datetime import datetime
import logging
from .Order import OrderId
from .Station import StationId
from .TaskStatus import TaskStatus
from .Item import ItemCounter, ItemId

from .database_order_manager import DatabaseOrderManager


# Set up logging
logger = logging.getLogger("test_database_order_manager")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)


class TestDatabaseOrderManager(unittest.TestCase):
    """Set of tests for the DBM"""

    def setUp(self) -> None:
        self.dbm = DatabaseOrderManager(":memory:")  # Use in-memory DB
        self.dbm.reset()  # Since we're testing, clear tables first and start fresh

    def test_finish_order(self):
        returned_orders = []
        for i in range(3):
            order = self.dbm.add_order(created_by=1,
                                       created=datetime.now(),
                                       items=ItemCounter(
                                           map(ItemId, [1, 2, 2, 4, i])),
                                       description="order with 5 items")
            returned_orders.append(order)

        orders = self.dbm.get_orders()
        assert orders == returned_orders
        assert len(orders) == 3

        stations = self.dbm.get_stations()
        self.dbm.assign_order_to_station(OrderId(1), StationId(1))
        self.dbm.assign_order_to_station(OrderId(3), StationId(2))
        stations = self.dbm.get_stations()
        logger.info('----')
        logger.info(f'Orders: {orders}')
        logger.info(f'Stations: {stations}')
        logger.info('----')

        self.dbm.add_item_to_station(StationId(1), ItemId(0), quantity=1)
        self.dbm.add_item_to_station(StationId(1), ItemId(1), quantity=1)
        self.dbm.add_item_to_station(StationId(1), ItemId(2), quantity=2)
        self.dbm.add_item_to_station(StationId(1), ItemId(4), quantity=1)

        self.dbm.add_item_to_station(StationId(2), ItemId(2), quantity=1)
        self.dbm.add_item_to_station(StationId(2), ItemId(2), quantity=1)

        orders = self.dbm.get_orders()
        stations = self.dbm.get_stations()

        tasks = self.dbm.get_tasks()
        incomplete_tasks = [
            task for task in tasks if task.status != TaskStatus.COMPLETE]

        logger.info('-----')
        logger.info(f'Orders: {orders}')
        logger.info(f'Stations: {stations}')
        logger.info(f'Tasks: {tasks}')
        logger.info(f'Incomplete Tasks: {incomplete_tasks}')
        logger.info('-----')

        self.dbm.con.close()
        assert len(incomplete_tasks) == 3

    def test_add_station(self):
        # Add a station and confirm count increases by one
        stations = self.dbm.get_stations()
        assert len(stations) == 3  # hardcoded default for init_stations
        self.dbm.add_station()
        stations = self.dbm.get_stations()
        assert len(stations) == 4

    def test_clear_init_station(self):
        # Add a station and confirm count increases by one
        stations = self.dbm.get_stations()
        assert len(stations) == 3  # hardcoded default for init_stations
        self.dbm.add_station()
        stations = self.dbm.get_stations()
        assert len(stations) == 4

    def test_assign_order_to_station(self):
        station_id = StationId(1)
        assert self.dbm.get_station_order(station_id) is None

        # Add order to station
        order1 = self.dbm.add_order(ItemCounter(), created_by=123)
        self.dbm.assign_order_to_station(order1.order_id, station_id)

        # Confirm station has order
        result_order_id = self.dbm.get_station_order(station_id)
        assert result_order_id is order1.order_id

        # Confirm clear station removes order
        self.dbm.clear_station(station_id)
        assert self.dbm.get_station_order(station_id) is None

    def test_get_station_with_order_id(self):
        station1_id = StationId(1)
        station2_id = StationId(2)
        # Add orders to stations
        order1 = self.dbm.add_order(ItemCounter(), created_by=123)
        order2 = self.dbm.add_order(ItemCounter(), created_by=123)
        self.dbm.assign_order_to_station(order1.order_id, station1_id)
        self.dbm.assign_order_to_station(order2.order_id, station2_id)

        # Confirm get station by order id for both stations
        result_station1_id = self.dbm.get_station_with_order_id(
            order1.order_id)
        result_station2_id = self.dbm.get_station_with_order_id(
            order2.order_id)
        assert result_station1_id == station1_id
        assert result_station2_id == station2_id

        # Confirm no station id if it doesn't exist
        result_station_id = self.dbm.get_station_with_order_id(1234)
        assert result_station_id is None

    def test_get_station_and_tasks(self):
        station_id = StationId(2)
        # Add order with 2 items to station 2
        order1 = self.dbm.add_order(ItemCounter(
            [ItemId(4), ItemId(5), ItemId(4)]), created_by=123)
        self.dbm.assign_order_to_station(order1.order_id, station_id)

        # Get stations and tasks
        # Expecting:
        #   Station 1: AVAILABLE []
        #   Station 2: Order 1
        #     [Task 1 [OPEN]: Item 4x2 to Station 2, Task 2 [OPEN]: Item 5x1 to Station 2]
        #   Station 3: AVAILABLE []
        station_tasks = self.dbm.get_stations_and_tasks()
        for station, tasks in station_tasks:
            # Confirm station with order has 3 tasks for each item
            if station.station_id == station_id:
                assert station.has_order()
                assert station.order_id == order1.order_id
                # Expecting 2 tasks: [2 of Item 4, 1 of Item 5]
                assert len(tasks) == 2
                assert tasks[0].item_id == 4
                assert tasks[0].quantity == 2
                assert tasks[1].item_id == 5

    def test_add_item_to_station(self):
        station_id = StationId(1)
        item1 = ItemId(456)
        # Add order with 1 item to station
        order1 = self.dbm.add_order(ItemCounter([item1]), created_by=123)
        self.dbm.assign_order_to_station(order1.order_id, station_id)

        # Confirm station not yet cleared
        station = self.dbm.get_station(station_id)
        assert station.is_available() is False

        # add only item to station, completing the only task
        self.dbm.add_item_to_station(station_id, item1)
        
        # Confirm station is cleared
        station = self.dbm.get_station(station_id)
        assert station.is_available() is True

    def test_fill_station(self):
        order1 = self.dbm.add_order(ItemCounter(), created_by=123)
        # Add order to first available station
        self.dbm.fill_available_station()

        # Confirm a station has an order
        result_station_id = self.dbm.get_station_with_order_id(
            order1.order_id)
        assert result_station_id is not None
        
        # TODO : Add unit tests for following functions
        # self.dbm.get_incomplete_station_tasks
    
    def test_get_incomplete_station_tasks(self):
        station_id = StationId(1)
        item1 = ItemId(456)

        # Add order with 1 item to station
        order1 = self.dbm.add_order(ItemCounter([item1]), created_by=123)
        self.dbm.assign_order_to_station(order1.order_id, station_id)

        tasks = self.dbm.get_incomplete_station_tasks(station_id)
        assert len(tasks) == 1
        task = tasks[0]
        assert task.order_id == order1.order_id
        assert task.item_id == item1
        assert task.quantity == 1
        assert task.status == TaskStatus.OPEN


if __name__ == '__main__':
    unittest.main()
