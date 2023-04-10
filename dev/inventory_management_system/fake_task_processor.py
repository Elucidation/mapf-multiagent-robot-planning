import time
import random
from .database_order_manager import DatabaseOrderManager
from .TaskStatus import TaskStatus

db_name = "orders.db"
dboi = DatabaseOrderManager(db_name)


# Checks for any tasks, completes the latest one
step_delay = [0.2, 0.8]
task_complete_delay = [0.2, 0.6]
no_task_delay = 5

while True:
    # Get task (item X to station Y)
    tasks = dboi.get_tasks(query_status=TaskStatus.OPEN, N=1)
    if len(tasks) == 0:
        print(f'No Tasks at the moment, sleeping 5 seconds')
        time.sleep(no_task_delay)
        continue
    
    task = tasks[0]
    print(f'Received Task {task}')

    # Take 1-5 sec to complete task
    delay = task_complete_delay[0] + random.random() * (task_complete_delay[1]-task_complete_delay[0])
    print(f" waiting {delay} seconds")
    time.sleep(delay)

    # Submit task complete
    dboi.add_item_to_station(task.station_id, task.item_id)
    print(f'Finished {task}')

    # Delay till next task
    delay = step_delay[0] + random.random() * (step_delay[1]-step_delay[0])
    print(f" waiting {delay} seconds")
    time.sleep(delay)