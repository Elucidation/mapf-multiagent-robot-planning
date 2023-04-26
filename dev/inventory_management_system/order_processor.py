"""Process orders in database by filling available stations with orders."""
import logging
import sys
import time
from .database_order_manager import DatabaseOrderManager, MAIN_DB

# Set up logging
def create_logger():
    logging.basicConfig(filename='order_processor_logger.log', encoding='utf-8', filemode='w',
                        level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _logger = logging.getLogger('order_processor_logger')
    _logger.setLevel(logging.DEBUG)
    stream_logger = logging.StreamHandler()
    stream_logger.setLevel(logging.INFO)
    _logger.addHandler(stream_logger)
    return _logger

logger = create_logger()



if __name__ == '__main__':
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
