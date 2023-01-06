from database_order_manager import DatabaseOrderManager, MAIN_DB
import logging
import sys
import time

# Set up logging
logger = logging.getLogger("order_processor_logger")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

if __name__ == '__main__':
    db_orders = DatabaseOrderManager(MAIN_DB)

    if 'reset' in sys.argv:
        print('Resetting database')
        db_orders.reset()  # Clear tables

    logger.info("Checking for new orders / assigning orders to stations...")

    # Loop indefinitely, does the following:
    # - Check if any stations available and fill with an open order if it exists
    delay_s = 1
    while True:
        if db_orders.fill_available_station():
            logger.info('Assigned an order to a station.')
        time.sleep(delay_s)
