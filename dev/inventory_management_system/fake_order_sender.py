"""Fake order creator adds fake orders to the DB"""
import time
import random
import logging
import sys
from .Item import ItemCounter, ItemId
from .database_order_manager import DatabaseOrderManager, MAIN_DB

# Set up logging
logger = logging.getLogger("fake_order_sender")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

dbm = DatabaseOrderManager(MAIN_DB)

# fixed_item_list_options = [
#     [0, 1, 2, 3],
#     [2, 3, 3],
#     [1, 0, 1],
#     [0],
# ]

def send_random_order():
    """Creates new random order and adds it to the database"""
    item_list = ItemCounter(
        [ItemId(random.randint(0, 3)) for _ in range(random.randint(1, MAX_ITEMS))])
    order = dbm.add_order(item_list, created_by=1)
    logger.info(f'{i} - Send new order {order}')

if __name__ == '__main__':
    db_orders = DatabaseOrderManager(MAIN_DB)
    MAX_ITEMS = 4

    NUM_ORDERS = 1
    DELAY = 1

    # Pass num orders as param, delay as well
    if len(sys.argv) == 2:
        NUM_ORDERS = int(sys.argv[1])
    elif len(sys.argv) == 3:
        NUM_ORDERS = int(sys.argv[1])
        DELAY = int(sys.argv[2])
    
    for i in range(NUM_ORDERS):
        send_random_order()
        
        logger.info(f" waiting {DELAY:.2f} seconds")
        time.sleep(DELAY)
    print("Done")
