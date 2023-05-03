"""Process orders in database by filling available stations with orders."""
import os
import sys
import time
from logger import create_warehouse_logger
from .database_order_manager import DatabaseOrderManager, MAIN_DB


if __name__ == '__main__':
    logger = create_warehouse_logger('order_processor')
    if not os.path.isfile(MAIN_DB) and 'reset' not in sys.argv:
        raise FileNotFoundError(
            f'Expected to see DB "{MAIN_DB}" but did not find.')
    db_orders = DatabaseOrderManager(MAIN_DB)

    if 'reset' in sys.argv:
        print('Resetting database')
        db_orders.reset()  # Clear tables

    logger.info("Checking for new orders / assigning orders to stations...")

    # Loop indefinitely, does the following:
    # - Check if any stations available and fill with an open order if it exists
    DELAY_S = 1
    while True:
        with db_orders.con:
            if db_orders.fill_available_station():
                logger.info('Assigned an order to a station.')
            db_orders.commit()
        time.sleep(DELAY_S)
