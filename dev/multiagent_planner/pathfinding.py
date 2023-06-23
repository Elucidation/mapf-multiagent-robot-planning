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
# Heuristic Function is heuristic from pos_a to a fixed goal position that is set ahead
HeuristicFunction = Callable[[Position], float]
HeuristicFunctionGenerator = Callable[[Position], HeuristicFunction]


def get_manhattan_heuristic(pos_b):
    def manhattan_heuristic(pos_a: Position) -> float:
        return abs(pos_a[0] - pos_b[0]) + abs(pos_a[1] - pos_b[1])
    return manhattan_heuristic

def get_euclidean_heuristic(pos_b):
    def euclidean_heuristic(pos_a: Position) -> float:
        return math.sqrt((pos_a[0] - pos_b[0])**2 + (pos_a[1] - pos_b[1])**2)
    return euclidean_heuristic

def astar(graph, pos_a: Position, pos_b: Position, max_steps=10000,
          heuristic: Optional[HeuristicFunction] = None
          ) -> list[Position]:
    """A* search through graph from p

    Args:
        graph (2D np array): The grid to path through
        pos_a (Position): Start position
        pos_b (Position): Finish position
        max_steps (int, optional): Max number of steps. Defaults to 10000.
        heuristic (HeuristicFunction, optional): Heuristic used for pos_b

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

    # Default to euclidean heuristic if none was provided
    if (heuristic is None):
        heuristic = get_euclidean_heuristic(pos_b)

    # g-score: mapping of cost to get to point
    g_scores = {}

    path_track: dict[Position, Optional[Position]] = {}  # coord -> parent
    path_track[pos_a] = None
    g_scores[pos_a] = 0 # Starting position is zero

    # priority queue via heapq
    # f-score: f-score = g-score + h, best guess cost from node to goal
    f_score = g_scores[pos_a] + heuristic(pos_a)
    # priority queue contains (f-score, parent, pos)
    priority_queue: list[tuple[float, Optional[Position], Position]] = [
        (f_score, None, pos_a)]

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
            # cost from start to current to neighbor
            potential_g_score = g_scores[curr] + 1 # stepping a grid cell counts as 1
            # If neighbor available, and tentative g score better than existing if available.
            if (check_valid(neighbor) and
                ((neighbor not in g_scores) or potential_g_score < g_scores[neighbor])):
                g_scores[neighbor] = potential_g_score
                f_score = g_scores[neighbor] + heuristic(neighbor)
                new_node = (f_score, curr, neighbor)
                heapq.heappush(priority_queue, new_node)
                path_track[neighbor] = curr

    def get_path(curr_node):
        path = []
        while curr_node:
            path.append(curr_node)
            curr_node = path_track[curr_node]

        return list(reversed(path))

    # If path was found
    if curr == pos_b:
        return get_path(curr)
    # No path found
    return []


def st_astar(graph, pos_a: Position, pos_b: Position, dynamic_obstacles: set = set(),
             static_obstacles: set = set(), max_time=20,
             max_cells=10000, t_start=0, end_fast=False,
             heuristic: Optional[HeuristicFunction] = None,
             stats: dict = None,
             validate_ends = True) -> Path:
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
        max_cells (int, optional): max cells to visit. Defaults to 10000.
        t_start (int, optional): offset start time if this path starts later in dynamic obstacles. 
        end_fast (bool, optional): end as soon as destination reached vs waiting till max_time.
        heuristic (HeuristicFunction, optional): Heuristic (set for pos_b), Defaults to euclidean_heuristic
        stats (dict, optional): store run-time stats here if it exists. Defaults to None.
        validate_ends (bool, optional): Check if start and end positions are valid. Defaults to True.

    Raises:
        ValueError: _description_

    Returns:
        path (Path): A list of positions along the found path (or empty list if fail)
    """

    if graph[pos_a[0], pos_a[1]] > 0 or graph[pos_b[0], pos_b[1]] > 0:
        raise ValueError('Start/End locations in walls')
    if validate_ends and (pos_a in static_obstacles or pos_b in static_obstacles):
        return []  # Start/End in static obstacles

    def check_valid(stpos: PositionST) -> bool:
        (row, col, t) = stpos
        pos = stpos[:2]
        max_row, max_col = graph.shape
        if t > max_time+t_start:
            return False
        if not validate_ends and (pos == pos_a or pos == pos_b):
            return True # Start/end positions are considered valid at all times
        if row < 0 or row >= max_row:
            return False
        if col < 0 or col >= max_col:
            return False
        if graph[row, col] > 0:
            return False
        if pos in static_obstacles:
            return False
        if stpos in dynamic_obstacles:
            return False
        return True

    # Default to euclidean heuristic if none was provided
    if (heuristic is None):
        heuristic = get_euclidean_heuristic(pos_b)

    path_track: dict[PositionST, Optional[PositionST]] = {}  # coord -> parent
    curr: PositionST = (pos_a[0], pos_a[1], t_start)
    path_track[curr] = None
    # g-score: mapping of cost to get to point
    g_scores = {}
    g_scores[curr] = 0 # Starting position is zero

    # f-score: f-score = g-score + h, best guess cost from node to goal
    f_score = g_scores[curr] + heuristic(pos_a)

    # priority queue via heapq
    # f-score, parent, pos, time
    priority_queue: list[tuple[float, Optional[PositionST], PositionST]] = [(f_score, None, curr)]

    cells_visited = 0
    while (priority_queue and cells_visited < max_cells):
        _, _, curr = heapq.heappop(priority_queue)
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
            # cost from start to current to neighbor
            potential_g_score = g_scores[curr] + 1 # stepping a grid cell counts as 1
            # If neighbor available, and tentative g score better than existing if available.
            if (check_valid(neighbor) and
                ((neighbor not in g_scores) or potential_g_score < g_scores[neighbor])):
                g_scores[neighbor] = potential_g_score
                f_score = g_scores[neighbor] + heuristic(neighbor[:2])
                new_node: tuple[float, PositionST, PositionST] = (f_score, curr, neighbor)
                heapq.heappush(
                    priority_queue, new_node)
                path_track[neighbor] = curr
        cells_visited += 1

    def get_path(col):
        path = []
        while col:
            path.append(col[:2])  # remove time from path
            col = path_track[col]

        return list(reversed(path))

    path = []
    if curr[:2] == pos_b:
        path = get_path(curr)

    if stats is not None:
        stats['cells_visited'] = cells_visited
        stats['path_length'] = len(path)

    return path


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
