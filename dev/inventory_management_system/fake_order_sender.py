import time
import random
import logging
from .Item import ItemCounter, ItemId
from .database_order_manager import DatabaseOrderManager, MAIN_DB

# Set up logging
logger = logging.getLogger("fake_order_sender")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

dbm = DatabaseOrderManager(MAIN_DB)

fixed_item_list_options = [
    [1, 1, 2, 3],
    [2, 3, 3],
    [1, 2, 3],
    [3],
    [3, 5, 4, 4],
    [6, 4],
    [8, 8, 8, 8],
    [6, 7, 7, 8],
    [4, 5, 2, 2],
    [7, 8, 9],
]

for i in range(10):
    item_list = ItemCounter(map(ItemId,fixed_item_list_options[i % len(fixed_item_list_options)]))
    order = dbm.add_order(item_list, created_by=1)
    logger.info(f'{i} - Added new order {order}')
    
    delay = random.random() * 1.0  # random 0-5 second delay
    logger.info(f" waiting {delay:.2f} seconds")
    time.sleep(delay)
print("Done")
