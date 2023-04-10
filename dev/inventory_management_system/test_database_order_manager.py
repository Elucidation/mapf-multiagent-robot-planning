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

    def test_todo(self):
        pass
        # TODO : Add unit tests for following functions
        # self.dbm.get_station_order
        # self.dbm.add_station
        # self.dbm.get_station_order
        # self.dbm.add_station
        # self.dbm.get_station_with_order_id
        # self.dbm.get_stations_and_tasks
        # self.dbm.init_stations
        # self.dbm.clear_station
        # self.dbm.update_station
        # self.dbm.add_item_to_station
        # self.dbm.fill_available_station
        # self.dbm.get_incomplete_station_tasks
        # self.dbm.assign_order_to_station


if __name__ == '__main__':
    unittest.main()
