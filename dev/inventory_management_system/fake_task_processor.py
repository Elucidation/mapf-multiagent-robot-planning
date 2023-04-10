"""Fake Task processor retrieves open tasks and closes them at random times"""
import time
import random
from .database_order_manager import DatabaseOrderManager, MAIN_DB
from .TaskStatus import TaskStatus

dboi = DatabaseOrderManager(MAIN_DB)


# Checks for any tasks, completes the latest one
DELAY_STEP = [0.2, 0.8]
DELAY_TASK_COMPLETE = [0.2, 0.6]
DELAY_NO_TASK = 5

while True:
    # Get task (item X to station Y)
    tasks = dboi.get_tasks(query_status=TaskStatus.OPEN, limit_rows=1)
    if len(tasks) == 0:
        print('No Tasks at the moment, sleeping 5 seconds')
        time.sleep(DELAY_NO_TASK)
        continue

    task = tasks[0]
    print(f'Received Task {task}')

    # Take 1-5 sec to complete task
    delay = DELAY_TASK_COMPLETE[0] + random.random() * \
        (DELAY_TASK_COMPLETE[1]-DELAY_TASK_COMPLETE[0])
    print(f" waiting {delay} seconds")
    time.sleep(delay)

    # Submit task complete
    dboi.add_item_to_station(task.station_id, task.item_id)
    print(f'Finished {task}')

    # Delay till next task
    delay = DELAY_STEP[0] + random.random() * (DELAY_STEP[1]-DELAY_STEP[0])
    print(f" waiting {delay} seconds")
    time.sleep(delay)
