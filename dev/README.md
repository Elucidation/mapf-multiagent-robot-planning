# Automated Warehouse

This folder contains development scripts testing out an automated warehouse project.

## Modules:

### [`inventory_management_system`](inventory_management_system/)
A python module for tracking creating and tracking Orders, Items, Stations, and Tasks.
![IMS Web UI](inventory_management_system/ims_example.png)

### [`multiagent_planner`](multiagent_planner/)
A python module for finding paths in a 2D grid world for singular and multiple agents without collisions.
![test1 animation](../media/scenario4.gif)

### [`env_visualizer`](env_visualizer/)
A node module for seeing a live view of the tables of Orders/Stations and their status as they get completed.
![warehouse view 1](../media/warehouse_view1.jpg)

## Scripts

### [`world_sim.py`](world_sim.py)
Simulates the environment and robots.

### [`robot_allocator.py`](robot_allocator.py)
Manages Robot states and assigns Tasks to them, updating the warehouse as needed


### [`order_processor.py`]([inventory_management_system/order_processor.py])
Manages open orders, assigns to stations, creates tasks, etc.

---

- Orders with multiple items will be assigned to empty stations.
- Robots will be assigned Tasks to take items from pickup to assigned stations,
- when a station has all items in an order, the order is completed and removed from the station.
- The system runs indefinitely

# Running

Run commands from this `dev` folder.

Start order processor and reset the inventory management database:
```sh
python -m inventory_management_system.order_processor reset
```

Start the world simulator
```sh
python -m world_sim
```


Run the order/station live visualizer (Need [flask](https://flask.palletsprojects.com/en/2.2.x/installation/) installed)
```sh
flask --app inventory_management_system.order_tracking_web_server --debug run
```

Run the world (the robots, zones,etc. on a 2D grid) live visualizer
```sh
node env_visualizer
```


Create fake orders with:
```sh
python -m inventory_management_system.fake_order_sender
```

# Tests

Using the python unit testing framework.

```sh
python -m unittest
```