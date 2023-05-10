# Inventory Management System (IMS)

Prototyping of a simplified IMS system for MAPF point robots in a 2D gridworld.

![IMS Web UI](../../media/ims_example.png)
*Screenshot of live web UI for tracking orders (with items and quantities), stations and completed tasks*

A Scenario has a Grid, with Robots, Robot start/wait positions, Item pickup locations, and Stations.
Orders with multiple items will be assigned to empty stations.
Robots will be assigned Tasks to take items from pickup to assigned stations,
when a station has all items in an order, the order is completed and removed from the station.
The system runs until all orders are completed or an error occurs.

## Concepts

This system allows you to manage orders that consist of multiple items, track the items and tasks at different assembly stations, and monitor the progress of each order.

The IMS Database is a system to manage orders, items, and tasks in a production or assembly environment. Here's a simple explanation of each table:

1. `Order` table: Stores information about orders, including an order ID, who created it, when it was created, when it was finished, a description, and the order status.

2. `Item` table: Stores information about individual items.

3. `OrderItem` table: Represents the relationship between orders and items. It shows which items are part of an order and the quantity of each item in the order.

4. `Station` table: Stores information about workstations or assembly stations, including a station ID and the order currently being processed at the station.

5. `Task` table: Stores information about tasks associated with processing an order at a specific station.

* Order contains Items
* Stations consolidate Orders
* Tasks are to add Items to a Station

When a Station contains all items for an assigned order, the Order is ready to be sent/removed.
Assigning an Order to a Station marks the order `IN_PROGRESS`,
adds Tasks for each item in the order to that station, and assigns the order id to that station.

```sql
TABLE Order
order_id, created_by, created, finished, description, status

TABLE Item
item_id, name, description, color

TABLE OrderItem
order_id, item_id, quantity

TABLE Station
station_id, order_id

TABLE Task
task_id, station_id, order_id, item_id, quantity, status
```

## Flow

Order Request -> MQTT -> order_mqtt_to_db -> DB insert new open order

DB -> get open orders oldest N -> assign open order to empty station -> DB insert order-station + tasks for all items to station

DB -> get available tasks for robots oldest N -> assign tasks to available robots -> update DB

on task complete -> check DB if station has no tasks (ie. complete) -> complete order on DB

## Redis Flow

Generally Order Processor does the following in a loop, each loop is a step:
* Check for requested orders, ingest into new orders for a time
* Check for processed tasks and complete them, for a time
* Check if any stations are complete
* Check for new orders an assign them while stations/orders are available

More specifically:

New order requests come in to the queue 'orders:requested'

Order Processor does in a loop:
* ingest: try lpop from 'orders:requested', creates an order and appends to queue 'orders:new'
* finish tasks: tries to lpop 'tasks:processed', adding those items to station, and append task log to 'tasks:finished'
* complete stations: for any tasks finished in previous step, check if that station has all tasks finished
  if yes, clear station and add it to back onto the set 'stations:free', 
    complete the order for that station, appending finished order log to 'orders:finished'
* assign: checks if there exists members in the queue 'orders:new' and the set 'stations:free',
  if yes, lpops a new order from queue 'orders:new' and pops a station from 'stations:free',
    then it assigns the order to that station,
    also creating and appending many tasks to 'tasks:new' for each item in the order
  else: continues


keys: 'stations:free', 'station:count',
      'orders:requested', 'orders:new', 'orders:finished',
      'tasks:new', 'tasks:inprogress', 'tasks:processed', 'tasks:finished'