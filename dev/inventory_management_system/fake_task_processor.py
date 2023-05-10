"""
A fake task manager that continuously checks a database for new tasks.
When a new task is found, the code will complete the task and then wait for the next task.

The following variables are used:
* `delay_no_task`: An integer, the number of seconds to wait if no tasks are found.
* `delay_task_complete`: A tuple, the min and max number of seconds to wait to complete a task.
* `delay_step`: A tuple, the min and max number of seconds to wait between tasks.

The code performs the following steps:
1. Get a task from the database.
2. If no tasks are found, wait for 5 seconds and then repeat step 1.
3. Complete the task.
4. Commit the changes to the database.
5. Wait for the next task.
"""
import argparse
import os
import time
import random

import redis
from warehouse_logger import create_warehouse_logger

parser = argparse.ArgumentParser(
    prog='FakeTaskProcessor',
    description='Process tasks with random delays from the tasks:new queue')

parser.add_argument('-d', '--delay-step',
                    default=[0.2, 0.8],  nargs='+', type=float,
                    help='the min and max number of seconds to wait between tasks.')
parser.add_argument('-t', '--delay-task-complete', default=[0.2, 0.6], nargs='+', type=float,
                    help='the min and max number of seconds to wait to complete a task.')
parser.add_argument('-n', '--delay-no-task', default=5, type=float,
                    help='the number of seconds to wait if no tasks are found.')
args = parser.parse_args()


logger = create_warehouse_logger('fake_task_processor')


# Set up redis
REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))
redis_con = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
logger.info(f'Connecting to Redis {REDIS_HOST}:{REDIS_PORT}')


# Continuously check the database for new tasks.
logger.info('Checking for tasks...')
while True:
    # Get task (item X to station Y)
    # tasks = dboi.get_tasks(query_status=TaskStatus.OPEN, limit_rows=1)

    task_key = redis_con.lpop('tasks:new')  # Gets task key
    if not task_key:
        # logger.info('No Tasks at the moment, sleeping 5 seconds')
        time.sleep(args.delay_no_task)
        continue

    logger.info(f'Received Task {task_key}')
    # Add task key to set of tasks in progress
    redis_con.sadd('tasks:inprogress', task_key)

    # Take 1-5 sec to complete task
    # Get task group key, item_id and idx
    # There is a task group key: 'task:station:<id>:order:<id>' -> set(item_id, item_id...)
    #   Which has a set of all the individual task keys 'task:station:<id>:order:<id>:<item_id>:<idx>'
    task_group_key, item_id, idx = task_key.rsplit(':', 2)
    _, _, station_id, _, order_id = task_group_key.split(':')
    logger.info(
        f'Task Group {task_group_key}, moving item {item_id}'
        f'(#{idx}) to station {station_id} for order {order_id}...')

    delay = args.delay_task_complete[0] + random.random() * \
        (args.delay_task_complete[1]-args.delay_task_complete[0])
    logger.info(f" waiting {delay:.2f} seconds for task to complete.")
    time.sleep(delay)

    # Move task from in progress to processed (order processor will confirm it is finished)
    redis_con.srem('tasks:inprogress', task_key)
    redis_con.lpush('tasks:processed', task_key)
    logger.info(f'Processed {task_key}')
    # The order processor will pull the processed task from the queue,
    # add the item to the station, and finish the task

    # Delay till next task
    delay = args.delay_step[0] + random.random() * \
        (args.delay_step[1]-args.delay_step[0])
    logger.info(f" waiting {delay:.2f} seconds")
    time.sleep(delay)
