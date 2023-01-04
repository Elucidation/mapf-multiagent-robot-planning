# Live grid/robot + tasks visualizer

Node.js web server showing current grid and robots, live updates.
Tasks and robots assigned to the tasks are shown too.


World Sim
---
- Grid (size, obstacles)
- Time step (real-world rate vs sim rate, ex. 1 time step per real second)
- Robots (current pos, paths)
- Robots-Task assignment table
- Item Pickup table
- Station Location table

World Sim flow
- has loop iterating every time step, can be queries for current time step, grid state, robot positions, etc.
- Can be updated with new grid, new robots, robot positions, future paths for robots.
- Tracks current pos of robots based on paths and time step
- detects collisions/error states
- emits latest state every time step
- reads/updates from DB
 - Robot positions
 - Once for grid info?
 - Once from Item Pickup table to visualize locations on grid


# Path to complete

1 web viz, socket emit a state, show robot states - Complete
2 web viz, listen on another socket ?
3 world sim, init with defaults and 1 robot stationary, emit to web viz via socket on a loop ?
4 push a manual path to world sim for that robot via ?, push that path to web viz
5 two robots?