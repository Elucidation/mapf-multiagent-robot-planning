import unittest
# Basic test creation of a Database, assign orders, add items, check incomplete tasks etc.
from datetime import datetime
from Order import *
from Station import *
from TaskStatus import TaskStatus
from Item import ItemId
import logging
import os

from database_order_manager import DatabaseOrderManager


# Set up logging
logger = logging.getLogger("test_database_order_manager")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

class TestDatabaseOrderManager(unittest.TestCase):
    def test_database_order_manager(self):
        test_db_filename = "test2.db"
        dbm = DatabaseOrderManager(test_db_filename)

        # Since we're testing, clear tables first and start fresh
        dbm.reset()

        returned_orders = []
        for i in range(3):
            order = dbm.add_order(created_by=1,
                                created=datetime.now(),
                                items=ItemCounter(map(ItemId, [1, 2, 2, 4, i])),
                                description="order with 5 items")
            returned_orders.append(order)

        orders = dbm.get_orders()
        assert(orders == returned_orders)
        assert(len(orders) == 3)

        stations = dbm.get_stations()
        dbm.assign_order_to_station(OrderId(1), StationId(1))
        dbm.assign_order_to_station(OrderId(3), StationId(2))
        stations = dbm.get_stations()
        logger.info('----')
        logger.info(f'Orders: {orders}')
        logger.info(f'Stations: {stations}')
        logger.info('----')

        dbm.add_item_to_station(StationId(1), ItemId(0), quantity=1)
        dbm.add_item_to_station(StationId(1), ItemId(1), quantity=1)
        dbm.add_item_to_station(StationId(1), ItemId(2), quantity=2)
        dbm.add_item_to_station(StationId(1), ItemId(4), quantity=1)

        dbm.add_item_to_station(StationId(2), ItemId(2), quantity=1)
        dbm.add_item_to_station(StationId(2), ItemId(2), quantity=1)

        orders = dbm.get_orders()
        stations = dbm.get_stations()

        tasks = dbm.get_tasks()
        incomplete_tasks = [
            task for task in tasks if task.status != TaskStatus.COMPLETE]

        logger.info('-----')
        logger.info(f'Orders: {orders}')
        logger.info(f'Stations: {stations}')
        logger.info(f'Tasks: {tasks}')
        logger.info(f'Incomplete Tasks: {incomplete_tasks}')
        logger.info('-----')

        dbm.con.close()
        os.remove(test_db_filename)

        assert(len(incomplete_tasks) == 3)

if __name__ == '__main__':
    unittest.main()

