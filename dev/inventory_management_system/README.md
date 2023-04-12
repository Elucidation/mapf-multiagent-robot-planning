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

* Order contains Items
* Stations consolidate Orders
* Tasks are to add Items to a Station

When a Station contains all items for an assigned order, the Order is ready to be sent/removed.
Assigning an Order to a Station marks the order `IN_PROGRESS`,
adds Tasks for each item in the order to that station, and assigns the order id to that station.

```sql
TABLE Order 
order_id, created_by, creation_date, description, state
# state : open / active / complete / error

TABLE Item
item_id, item_title, item_description, item_color, item_xy

TABLE OrderItem
order_id, item_id, quantity

TABLE Station
station_id, order_id, station_xy

TABLE Task
station_id, item_id, quantity, state 
# state : open / active / complete / error
```

## Flow

Order Request -> MQTT -> order_mqtt_to_db -> DB insert new open order

DB -> get open orders oldest N -> assign open order to empty station -> DB insert order-station + tasks for all items to station

DB -> get available tasks for robots oldest N -> assign tasks to available robots -> update DB

on task complete -> check DB if station has no tasks (ie. complete) -> complete order on DB
