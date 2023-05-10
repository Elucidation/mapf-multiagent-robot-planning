"""Process orders in database by filling available stations with orders.
TODO : Transition this to using Redis for real-time, sqlite for logs/records

Instead of checking the DB for new orders, use redis pub/sub and sub.
Sub to messages from redis
- new order by fake order sender (add to DB & push into redis)
  Also create a task for every single item (so always quantity 1)
  Also try to assign a station in redis and DB?
- item added by robot allocator (check station)
  Try to clear a station if all items are there
  If an order gets completed, update it in DB too
  Also try to assign a new order to station in redis and DB?
"""
import time
import datetime
import json
import os
import sys

import redis
from warehouse_logger import create_warehouse_logger
from warehouses.warehouse_loader import load_warehouse_yaml
from .Item import ItemCounter, ItemId
from .Order import Order, OrderId
from .Station import StationId

logger = create_warehouse_logger('order_processor')


class OrderProcessor:
    """Processes new order requests and distributes to DBs"""

    def __init__(self, redis_db: redis.Redis, station_count=None, reset=False) -> None:
        self.r = redis_db
        self.step_start = None
        if reset:
            assert station_count is not None
            self.reset_redis()
            self.init_stations(station_count)

    def reset_redis(self):
        logger.warning('Resetting redis stations/orders/tasks')
        self.r.delete('stations:free', 'station:count',
                      'orders:requested', 'orders:new', 'orders:finished',
                      'tasks:new', 'tasks:inprogress', 'tasks:processed', 'tasks:finished')

        for key in self.r.scan_iter("station:*"):
            self.r.delete(key)
        for key in self.r.scan_iter("order:*"):
            self.r.delete(key)
        for key in self.r.scan_iter("task:*"):
            self.r.delete(key)

    def init_stations(self, station_count: int):
        self.r.set('station:count', station_count)
        # 1-indexed station ids
        self.station_ids = [idx for idx in range(1, station_count+1)]
        for station_id in self.station_ids:
            station_key = f'station:{station_id}'
            # Consider not setting stations at all when empty
            data = {'order': ''}
            self.r.hset(station_key, mapping=data)
            # Station starts free/available
            self.r.rpush('stations:free', station_key)

    def try_ingest_order_request(self):
        """Pop front of orders:requested and ingest order if exists.
        Returns order_key if ingested, None otherwise"""
        # Check for new order message requests
        # TODO : Consider pulling in more than 1 at a time, assuming ingest is atomic
        msg = self.r.lpop('orders:requested')
        if not msg:
            return None
        order_request = json.loads(msg)
        if 'items' not in order_request:
            logger.error(f'corrupt order request, dropping: {order_request}')
            return None
        if 'created' not in order_request:
            order_request['created'] = time.time()
        return self.ingest_order(order_request)

    def ingest_order(self, order_request: dict):
        """Create new order and add to orders:new, Returns order_key."""
        logger.info(f'Ingest request {order_request}')
        # Make sure items is of ItemCounter{ItemId: int} format
        items = ItemCounter({ItemId(int(item_id)): int(quantity)
                            for item_id, quantity in order_request['items'].items()})
        created = order_request.get('created', time.time())
        order_id = self.r.incr('order:id')
        order_key = f'order:{order_id}'
        data = {'order_id': order_id,
                'created': created, 'items': json.dumps(items)}

        # Add order {order_id:..., items:ItemCounter}
        self.r.hset(order_key, mapping=data)
        # Add order key to queue of new orders
        self.r.rpush('orders:new', order_key)

        logger.info(f'Inserted order into redis: {order_key} {data}')
        # Step will try to assign it to a station
        return order_key

    def step(self):
        # logger.info('--- Step Start')
        self.step_start = time.time()
        # Check for requested orders, ingest into new orders for a time
        MAX_INGEST_TIME_MS = 100
        order_keys = []
        while (time.time() - self.step_start) < MAX_INGEST_TIME_MS:
            order_key = self.try_ingest_order_request()
            if not order_key:
                break
            order_keys.append(order_key)

        if order_keys:
            logger.info(f'Ingested Orders: {order_keys}')

        # Check for processed tasks and complete them, for a time
        time_start = time.time()
        MAX_TASK_PROC_TIME_MS = 100
        task_group_keys = set()
        while (time.time() - time_start) < MAX_TASK_PROC_TIME_MS:
            task_key = self.r.rpop('tasks:processed')
            if not task_key:
                break
            task_group_key, _, _ = self.parse_task_key_to_group(task_key)
            self.add_item_to_station(task_key)
            task_group_keys.add(task_group_key)

        # Check if any stations are complete
        for task_group_key in task_group_keys:
            self.try_complete_station(task_group_key)

        # Check for new orders an assign them while stations/orders are available
        while self.try_assign_order_to_station():
            continue

    def sleep(self):
        STEP_RATE_MS = 1000
        if self.step_start:
            delay_ms = STEP_RATE_MS - (time.time() - self.step_start)
            if delay_ms < 0:
                return  # No sleep since alredady past delay
            time.sleep(delay_ms / 1000.0)
        else:
            time.sleep(delay_ms / 1000.0)

    def get_new_orders(self, limit=-1) -> list:
        """Returns the queue of new order ids"""
        return self.r.lrange('orders:new', 0, limit)

    def get_stations(self):
        return {station_id: self.r.hgetall(f'station:{station_id}')
                for station_id in self.station_ids}

    @staticmethod
    def parse_items_json(items_json: str) -> ItemCounter:
        return ItemCounter({ItemId(int(item_id)): int(quantity)
                            for item_id, quantity in json.loads(items_json).items()})

    def try_assign_order_to_station(self):
        """Try to assign a new order to a free station if they exist.
        Returns the task_group_key if a station was assigned"""
        if not self.r.exists('orders:new'):
            return None  # No new orders
        if not self.r.exists('stations:free'):
            return None  # No free stations

        order_key = self.r.lpop('orders:new')  # Removes from new orders queue
        # Makes station not free queue
        station_key = self.r.lpop('stations:free')

        # Load order items
        order_items = self.parse_items_json(self.r.hget(order_key, 'items'))
        # Station has none of those items yet
        items_in_station = {item_id: 0 for item_id in order_items}
        order_data = {'order': order_key,
                      'items_in_station': json.dumps(items_in_station),
                      'items_in_order': json.dumps(order_items)}

        # Assign order to station
        self.r.hset(station_key, mapping=order_data)
        logger.info(f'Assigning {order_key} to {station_key}')

        # Create tasks for that station (1 per item times quantity)
        # There is a task group key: 'task:station:<id>:order:<id>' -> set(item_id, item_id...)
        #   Which has a set of all the individual task keys 'task:station:<id>:order:<id>:<item_id>:<idx>'
        # Each of these task keys are pushed onto the tasks:new queue
        task_group_key = f'task:{station_key}:{order_key}'
        # Unique id for that task 'task:station:id:order:id:item_id:idx' for all items in order
        task_keys = [f'{task_group_key}:{item_id}:{idx}' for idx,
                     item_id in enumerate(order_items.elements())]
        # Set of all task keys for that specific station task
        self.r.sadd(task_group_key, *task_keys)
        # Also push all tasks onto new task queue
        self.r.rpush('tasks:new', *task_keys)
        logger.info(f'Pushed {len(task_keys)} tasks onto tasks:new')
        logger.info(f'Set {task_group_key} = set({task_keys})')

        return task_group_key

    @staticmethod
    def parse_task_key_to_ids(task_key: str):
        """Return (station_id, order_id, item_id, idx)"""
        # Task key contains it all 'task:station:<id>:order:<id>:<item_id>:<idx>'
        _, _, station_id, _, order_id, item_id, idx = task_key.split(':')
        return (StationId(int(station_id)), OrderId(int(order_id)), ItemId(int(item_id)), int(idx))

    @staticmethod
    def parse_task_key(task_key: str):
        """Return (task_group_key, station_key, order_key, item_id, idx)"""
        # Task key contains it all 'task:station:<id>:order:<id>:<item_id>:<idx>'
        (station_id, order_id, item_id,
         idx) = OrderProcessor.parse_task_key_to_ids(task_key)
        station_key = f'station:{station_id}'
        order_key = f'order:{order_id}'
        task_group_key = f'task:{station_key}:{order_key}'
        return (task_group_key, station_key, order_key, item_id, idx)

    @staticmethod
    def parse_task_group_key_to_ids(task_group_key: str):
        """Return (station_id, order_id)"""
        # Task key contains it all 'task:station:<id>:order:<id>'
        _, _, station_id, _, order_id = task_group_key.split(':')
        return (StationId(int(station_id)), OrderId(int(order_id)))

    @staticmethod
    def parse_task_group_key(task_group_key: str):
        """Return (station_key, order_key)"""
        # Task key contains it all 'task:station:<id>:order:<id>'
        (station_id, order_id) = OrderProcessor.parse_task_group_key_to_ids(
            task_group_key)
        station_key = f'station:{station_id}'
        order_key = f'order:{order_id}'
        return (station_key, order_key)

    @staticmethod
    def parse_task_key_to_group(task_key: str):
        """Return (task_group_key, item_id, idx)"""
        # Task key contains it all 'task:station:<id>:order:<id>:<item_id>:<idx>'
        task_group_key, item_id, idx = task_key.rsplit(':', 2)
        return (task_group_key, ItemId(int(item_id)), int(idx))

    def add_item_to_station(self, task_key: str):
        (task_group_key, station_key, _, item_id, _) = self.parse_task_key(task_key)

        # Update item count for key:value items_in_station
        items_in_station = self.parse_items_json(
            self.r.hget(station_key, 'items_in_station'))
        # Note: Critical that item_id stays int at all times or we get two keys
        # Having '#' and # with json loads/dumps breaks
        assert (isinstance(item_id, int))
        items_in_station[item_id] += 1
        self.r.hset(station_key, 'items_in_station',
                    json.dumps(items_in_station))
        # tmp = self.r.hget(station_key, 'items_in_station')
        # Add item to station
        logger.info(f'Added item {item_id} to {station_key}')

        # Remove the task key from the task group
        self.r.srem(task_group_key, task_key)

        self.r.xadd('tasks:finished', {'task_key': task_key})
        # Note : If error, move task back into tasks:new head otherwise
        logger.info(f'Finished task {task_key} item {item_id}')

    def try_complete_station(self, task_group_key: str):
        """Input task_group_key = f'task:station:id:order:id' """
        if self.r.scard(task_group_key) == 0:
            (station_key, _) = self.parse_task_group_key(task_group_key)
            self.complete_station(station_key)

    def complete_station(self, station_key: str):
        # Validate number of items is the same
        order_key, items_in_station, items_in_order = self.r.hmget(
            station_key, ['order', 'items_in_station', 'items_in_order'])
        items_in_station = self.parse_items_json(items_in_station)
        items_in_order = self.parse_items_json(items_in_order)
        diff = items_in_order - items_in_station
        if diff:
            logger.error(
                'ERROR: Expected all items in station, but in station'
                f' {items_in_station} vs order {items_in_order} = {diff}')
            return

        logger.info(
            f'Fulfilled/Complete Station {station_key} order {order_key}')
        # All items added, clear station and finish order
        self.r.hdel(station_key, 'items_in_station', 'items_in_order')
        self.r.hset(station_key, 'order', '')
        self.r.rpush('stations:free', station_key)
        # Clear order from hash set and push into orders:finished stream
        finished_order = self.r.hgetall(order_key)
        finished_order['station'] = station_key
        self.r.xadd('orders:finished', finished_order)
        self.r.delete(order_key)


if __name__ == '__main__':
    _, _, _, station_zones = load_warehouse_yaml(
        os.getenv('WAREHOUSE_YAML', 'warehouses/warehouse3.yaml'))

    # Set up redis
    REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))
    redis_con = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_timeout=1)
    logger.info(f'Redis server {REDIS_HOST}:{REDIS_PORT}')

    DO_RESET = 'reset' in sys.argv
    order_processor = OrderProcessor(
        redis_con, len(station_zones), reset=DO_RESET)
    logger.info("Checking for new orders / assigning orders to stations...")
    while True:
        try:
            order_processor.step()
            order_processor.sleep()
        except redis.exceptions.TimeoutError as e:
            continue

    # # Loop indefinitely, does the following:
    # # - Check if any stations available and fill with an open order if it exists
    # DELAY_S = 1
    # while True:
    #     with db_orders.con:
    #         if db_orders.fill_available_station():
    #             logger.info('Assigned an order to a station.')
    #         db_orders.commit()
    #     time.sleep(DELAY_S)
