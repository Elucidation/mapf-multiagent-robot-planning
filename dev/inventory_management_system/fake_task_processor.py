from database_order_manager import DatabaseOrderManager
import time
import random


db_name = "orders.db"
dboi = DatabaseOrderManager(db_name)

while True:
    # Get task (item X to station Y)
    tasks = dboi.get_latest_tasks(N=1)
    if len(tasks) == 0:
        print(f'No Tasks at the moment, sleeping 5 seconds')
        time.sleep(5)
        continue
    
    task = tasks[0]
    print(f'Received Task {task}')

    # Take 1-5 sec to complete task
    delay = 1.0 + random.random() * 4.0  # random 0-5 second delay
    print(f" waiting {delay} seconds")
    time.sleep(delay)

    # Submit task complete
    dboi.add_item_to_station(task.station_id, task.item_id)
    print(f'Finished {task}')

    # Delay till next task
    delay = random.random() * 5.0  # random 0-5 second delay
    print(f" waiting {delay} seconds")
    time.sleep(delay)