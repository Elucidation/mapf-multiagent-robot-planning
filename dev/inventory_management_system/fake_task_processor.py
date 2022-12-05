from database_order_manager import DatabaseOrderManager
import time
import random


db_name = "orders.db"
dboi = DatabaseOrderManager(db_name)


# Check if any available stations, if so, choose 1
# Check for first open order
# If both exist, assign order to station

def fill_available_station():
    stations = dboi.get_available_stations(N=1)
    if len(stations) == 0:
        return
    orders = dboi.get_orders(N=1, status='OPEN')
    if len(orders) == 0:
        return
    dboi.assign_order_to_station(order_id=orders[0].order_id, station_id=stations[0].station_id)
    print(f'Filled {stations[0]} with {orders[0]}')

# Checks for any tasks, completes the latest one


step_delay = [0.2, 0.8]
task_complete_delay = [0.2, 0.6]
no_task_delay = 5

while True:
    fill_available_station()

    # Get task (item X to station Y)
    tasks = dboi.get_latest_tasks(N=1)
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