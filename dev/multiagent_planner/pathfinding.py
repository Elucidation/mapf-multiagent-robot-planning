"""A* and STA* pathfinding algorithms."""
import heapq
from collections import defaultdict
import math
from typing import Callable, Optional

# Type Aliases
Position = tuple[int, int]  # (row, col)
PositionST = tuple[int, int, int]  # (row, col, time)
Collision = tuple[int, int, int, int]  # (path_idx, row, col, time)
Path = list[Position]
PathST = list[PositionST]
HeuristicFunction = Callable[[Position, Position], float]


def manhattan_heuristic(pos_a: Position, pos_b: Position) -> float:
    return abs(pos_a[0] - pos_b[0]) + abs(pos_a[1] - pos_b[1])


def euclidean_heuristic(pos_a: Position, pos_b: Position) -> float:
    return math.sqrt((pos_a[0] - pos_b[0])**2 + (pos_a[1] - pos_b[1])**2)


def astar(graph, pos_a: Position, pos_b: Position, max_steps=10000,
          heuristic: HeuristicFunction = euclidean_heuristic) -> list[Position]:
    """A* search through graph from p

    Args:
        graph (2D np array): The grid to path through
        pos_a (Position): Start position
        pos_b (Position): Finish position

    Raises:
        ValueError: If start/end positions are in walls or out of grid

    Returns:
        list[Position]: path from start to finish, or empty list.
    """
    # graph is NxN int array, obstacles are non-zero
    # pos_a and pos_b are tuple positions (row,col) in graph

    if graph[pos_a[0], pos_a[1]] > 0 or graph[pos_b[0], pos_b[1]] > 0:
        raise ValueError('Start/End locations in walls')

    def check_valid(pos: Position) -> bool:
        max_row, max_col = graph.shape
        if pos[0] < 0 or pos[0] >= max_row:
            return False
        if pos[1] < 0 or pos[1] >= max_col:
            return False
        if graph[pos[0], pos[1]] > 0:
            return False
        return True

    close_set = set()
    path_track: dict[Position, Optional[Position]] = {}  # coord -> parent
    path_track[pos_a] = None
    close_set.add(pos_a)

    # priority queue via heapq
    # heuristc_score, parent, pos
    priority_queue: list[tuple[float, Optional[Position], Position]] = [
        (heuristic(pos_a, pos_b), None, pos_a)]

    cells_visited = 0
    while (priority_queue or cells_visited < max_steps):
        _, _, curr = heapq.heappop(priority_queue)
        cells_visited += 1
        if curr == pos_b:
            break

        row, col = curr
        neighbors: list[Position] = [
            (row-1, col), (row+1, col), (row, col-1), (row, col+1)]
        for neighbor in neighbors:
            if neighbor not in close_set and check_valid(neighbor):
                new_node = (heuristic(neighbor, pos_b), curr, neighbor)
                heapq.heappush(priority_queue, new_node)
                close_set.add(neighbor)
                path_track[neighbor] = curr

    def get_path(curr_node):
        path = []
        while curr_node:
            path.append(curr_node)
            curr_node = path_track[curr_node]

        return list(reversed(path))

    # print(f'astar searched {cells_visited} cells')

    # If path was found
    if curr == pos_b:
        return get_path(curr)
    # No path found
    return []


def st_astar(graph, pos_a: Position, pos_b: Position, dynamic_obstacles: set = set(),
             static_obstacles: set = set(), max_time=20,
             maxiters=10000, t_start=0, end_fast=False,
             heuristic: HeuristicFunction = euclidean_heuristic) -> Path:
    """Space-Time A* search.

    Each tile is position.
    Look at graph as an NxNxT loaf (where T = time) with cells as position at a time,
    pos_a and pos_b are tuple positions (row,col) in graph.

    Args:
        graph (_type_): NxN int array, obstacles are non-zero
        pos_a (Position): _description_
        pos_b (Position): _description_
        dynamic_obstacles (set): set{(row,col,t), ...} of obstacles to avoid. Defaults to set().
        static_obstacles (set): set{(row,col), ...} of obstacles to avoid. Defaults to set().
        max_time (int, optional): max time to search up to. Defaults to 20.
        maxiters (int, optional): _description_. Defaults to 10000.
        t_start (int, optional): offset start time if this path starts later in dynamic obstacles. 
        end_fast (bool, optional): end as soon as destination reached vs waiting till max_time.
        heuristic (HeuristicFunction, optional): Heuristic used, Defaults to euclidean_heuristic

    Raises:
        ValueError: _description_

    Returns:
        path (Path): A list of positions along the found path (or empty list if fail)
    """

    if graph[pos_a[0], pos_a[1]] > 0 or graph[pos_b[0], pos_b[1]] > 0:
        raise ValueError('Start/End locations in walls')
    if pos_a in static_obstacles or pos_b in static_obstacles:
        return []  # Start/End in static obstacles

    def check_valid(stpos: PositionST) -> bool:
        (row, col, t) = stpos
        max_row, max_col = graph.shape
        if t > max_time+t_start:
            return False
        if row < 0 or row >= max_row:
            return False
        if col < 0 or col >= max_col:
            return False
        if graph[row, col] > 0:
            return False
        if (row, col) in static_obstacles:
            return False
        if stpos in dynamic_obstacles:
            return False
        return True

    close_set = set()
    path_track: dict[PositionST, Optional[PositionST]] = {}  # coord -> parent
    curr: PositionST = (pos_a[0], pos_a[1], t_start)
    path_track[curr] = None
    close_set.add(curr)

    # priority queue via heapq
    # heuristc_score, parent, pos, time
    priority_queue: list[tuple[float, Optional[PositionST], PositionST]] = [
        (heuristic(pos_a, pos_b), None, curr)]

    i = 0
    while (priority_queue and i < maxiters):
        _, _, curr = heapq.heappop(priority_queue)
        close_set.add(curr)
        # End once destination reached
        if end_fast and curr[:2] == pos_b:
            break
        # Only quit at max_time
        if curr == (pos_b[0], pos_b[1], max_time):
            break

        row, col, t = curr

        # next cell one time step forward
        neighbors: list[PositionST] = [(row, col, t+1),
                                       (row-1, col, t+1),
                                       (row+1, col, t+1),
                                       (row, col-1, t+1),
                                       (row, col+1, t+1)]
        for neighbor in neighbors:
            if neighbor not in close_set and check_valid(neighbor):
                new_node: tuple[float, PositionST, PositionST] = (
                    heuristic(neighbor[:2], pos_b), curr, neighbor)
                heapq.heappush(
                    priority_queue, new_node)
                # close_set.add(neighbor)
                path_track[neighbor] = curr
        i += 1

    def get_path(col):
        path = []
        while col:
            path.append(col[:2])  # remove time from path
            col = path_track[col]

        return list(reversed(path))

    # If path was found
    if curr[:2] == pos_b:
        return get_path(curr)
    # No path found
    return []


def find_all_collisions(paths: list[list[Position]]):
    collisions = []
    for i, path_i in enumerate(paths):
        for j in range(i+1, len(paths)):
            collisions.extend(find_collisions(path_i, paths[j], label=j))
    return collisions


def find_collisions(path1: list[Position],
                    path2: list[Position], label: int = 1) -> list[Collision]:
    # Find any vertex and edge collisions, and return a list of (path_idx,row,col,t) collisions
    # for edge collisions, obstacles are for path2 to avoid

    # extend shorter path with waits
    # tmax = min(len(path1), len(path2))
    if not path1 or not path2:
        return []
    diff = len(path2) - len(path1)
    if diff > 0:
        # if path 2 longer
        path1.extend(diff*[path1[-1]])
    elif diff < 0:
        path2.extend((-diff)*[path2[-1]])

    tmax = len(path1)
    collisions: list[Collision] = []  # (path_name,row,col,t)
    for t in range(tmax):
        # vertex collision
        if path1[t] == path2[t]:
            collisions.append((label, path1[t][0], path1[t][1], t))

        # edge collision, robots swap locations, just add all times
        if (t-1 >= 0) and path1[t-1] == path2[t] and path1[t] == path2[t-1]:
            # obstacle for path 2
            collisions.append((label, path2[t][0], path2[t][1], t))

            # todo: add dynamic obstacles with path reference
            # collisions.append([path1[t-1][0], path1[t-1][1], t])
            # collisions.append([path1[t][0], path1[t][1], t])

    return collisions


def mapf0(grid, starts, goals):
    # For several robots with given start/goal locations and a grid
    # Get paths for all, do all as independent
    #  - independent A-star for each as initial paths
    assert len(starts) == len(goals)
    paths = []
    for i, start in enumerate(starts):
        paths.append(astar(grid, start, goals[i]))
    return paths


def mapf1(grid, starts, goals, maxiter=5, max_time=20):
    # For several robots with given start/goal locations and a grid
    # Attempt to find paths for all that don't collide
    # Attempt 1:
    #  - independent A-star for each as initial paths
    #  - check for collisions as dynamic obstacles
    #  - st_astar for paths (priority ordering) that collide until no collisions
    assert len(starts) == len(goals)
    paths = []
    for i, start in enumerate(starts):
        paths.append(astar(grid, start, goals[i]))

    collisions = find_all_collisions(paths)
    # dict of collisions per path
    path_collisions = defaultdict(set)
    for collision in collisions:
        path_idx, row, col, t = collision
        path_collisions[path_idx].add((row, col, t))

    if not collisions:
        return paths

    # list of (path_idx, row, col, t)
    for i in range(maxiter):
        # print(f'{i} | Trying to remove collisions: {collisions}')
        path_idx, row, col, t = collisions[0]

        # Add all collisions associated with this path
        # dynamic_obstacles = {(row,col,t) : True}
        dynamic_obstacles = path_collisions[path_idx]
        # print('Before:')
        # print(paths[path_idx])
        paths[path_idx] = st_astar(
            grid, starts[path_idx], goals[path_idx], dynamic_obstacles, max_time=max_time)
        # print('After:')
        # print(paths[path_idx])
        collisions = find_all_collisions(paths)
        if not collisions:
            break

        # Note: Keeps old dynamic obstacles, not optimal
        for collision in collisions:
            path_idx, row, col, t = collision
            path_collisions[path_idx].add((row, col, t))

    return paths
