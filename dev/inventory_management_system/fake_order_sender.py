"""Fake order creator adds fake orders to the DB"""
import argparse
import json
import os
import random
import time
import redis

from warehouse_logger import create_warehouse_logger
from .Item import ItemCounter, ItemId

# Set up logging
logger = create_warehouse_logger('fake_order_sender')

parser = argparse.ArgumentParser(
    prog='FakeOrderSender',
    description='Adds new random order requests onto the redis orders:requested queue')

parser.add_argument('-n', '--num-orders', default=1, type=int)
parser.add_argument('-d', '--delay', default=1.0, type=float)
parser.add_argument('--max-items', default=4, type=int)
parser.add_argument('--max-item-id', default=5, type=int)
args = parser.parse_args()


# Set up redis
REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))
redis_con = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
logger.info(f'Connecting to Redis {REDIS_HOST}:{REDIS_PORT}')

while True:
    try:
        if redis_con.ping():
            break
        else:
            logger.warning(
                f'Ping failed for redis server {REDIS_HOST}:{REDIS_PORT}, waiting')
    except redis.ConnectionError:
        logger.error(
            f'Redis unable to connect {REDIS_HOST}:{REDIS_PORT}, waiting')
    time.sleep(2)


def send_new_order_request():
    """Creates new random order and publishes to redis ims.new_order channel"""
    item_list = ItemCounter(
        [ItemId(random.randint(0, args.max_item_id)) for _ in range(random.randint(1, args.max_items))])
    order_request_queue = 'orders:requested'
    msg = json.dumps({'items': item_list})
    redis_con.rpush(order_request_queue, msg)
    logger.info(
        f'{i} - Added new order request to {order_request_queue} : {msg}')


logger.info("Starting publishing fake orders")
random.seed(1234)  # Use a fixed seed to make this repeatable
for i in range(args.num_orders):
    send_new_order_request()

    logger.info(f" waiting {args.delay:.2f} seconds")
    time.sleep(args.delay)
logger.info("Done")
