# Basic test creation of a Database, assign orders, add items, check incomplete tasks etc.
from datetime import datetime
from Order import *
from Station import *
from TaskStatus import TaskStatus
from Item import ItemId
import logging

from database_order_manager import DatabaseOrderManager


# Set up logging
logger = logging.getLogger("test_database_order_manager")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

def test_database_order_manager(test_db_name="test2.db"):
    dboi = DatabaseOrderManager(test_db_name)

    # Since we're testing, clear tables first and start fresh
    dboi.reset()

    returned_orders = []
    for i in range(3):
        order = dboi.add_order(created_by=1,
                               created=datetime.now(),
                               items=ItemCounter(map(ItemId, [1, 2, 2, 4, i])),
                               description="order with 5 items")
        returned_orders.append(order)

    orders = dboi.get_orders()
    assert(orders == returned_orders)
    assert(len(orders) == 3)

    stations = dboi.get_stations()
    dboi.assign_order_to_station(OrderId(1), StationId(1))
    dboi.assign_order_to_station(OrderId(3), StationId(2))
    stations = dboi.get_stations()
    logger.info('----')
    logger.info(f'Orders: {orders}')
    logger.info(f'Stations: {stations}')
    logger.info('----')

    dboi.add_item_to_station(StationId(1), ItemId(0), quantity=1)
    dboi.add_item_to_station(StationId(1), ItemId(1), quantity=1)
    dboi.add_item_to_station(StationId(1), ItemId(2), quantity=2)
    dboi.add_item_to_station(StationId(1), ItemId(4), quantity=1)

    dboi.add_item_to_station(StationId(2), ItemId(2), quantity=1)
    dboi.add_item_to_station(StationId(2), ItemId(2), quantity=1)

    orders = dboi.get_orders()
    stations = dboi.get_stations()

    tasks = dboi.get_tasks()
    incomplete_tasks = [
        task for task in tasks if task.status != TaskStatus.COMPLETE]

    logger.info('-----')
    logger.info(f'Orders: {orders}')
    logger.info(f'Stations: {stations}')
    logger.info(f'Tasks: {tasks}')
    logger.info(f'Incomplete Tasks: {incomplete_tasks}')
    logger.info('-----')

    assert(len(incomplete_tasks) == 3)

if __name__ == "__main__":
    test_database_order_manager()
