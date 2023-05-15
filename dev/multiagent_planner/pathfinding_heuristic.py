# This folder provides a function for generating an optimal heuristic table for a given grid
# optimal as in A* shortest path from any open cell to any other open cell
from collections import deque
import functools
import time
import numpy as np
from .pathfinding import astar, Position

grid = np.array([
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
])


def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # print(f'{func.__name__!r} Start')
        t_start = time.perf_counter()
        result = func(*args, **kwargs)
        t_end = time.perf_counter()
        print(
            f'{func.__name__!r} End. Took {(t_end - t_start)*1000:.3f} ms')
        return result
    return wrapper


# @timeit
def get_distances(grid, start: Position):
    # start is [row, col] of grid (2d array, 0 is open, 1 is wall)
    # We will use -1 to represent inaccessible areas
    distances = -np.ones_like(grid)

    # Directions for moving up, down, left, right
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    # Create a queue for the BFS
    queue = deque([start])

    # Set the distance at the start cell to be 0
    distances[start[0], start[1]] = 0

    while queue:
        current = queue.popleft()
        for dx, dy in directions:
            new_x, new_y = current[0] + dx, current[1] + dy
            if (0 <= new_x < grid.shape[0]) and (0 <= new_y < grid.shape[1]):
                if grid[new_x, new_y] == 0 and distances[new_x, new_y] == -1:
                    distances[new_x, new_y] = distances[current[0],
                                                        current[1]] + 1
                    queue.append((new_x, new_y))
    return distances


# print(grid)
# print(get_distances(grid, start_pt))


@timeit
def build_true_heuristic(grid):
    heuristic_dict = {}
    for pos in np.argwhere(grid == 0):
        heuristic_dict[tuple(pos)] = get_distances(grid, pos)
    return heuristic_dict


heuristic_dict = build_true_heuristic(grid)
def true_heuristic(pos_a: Position, pos_b: Position) -> float:
    return float(heuristic_dict[pos_b][pos_a])

start_pt = Position([7, 2])
goal_pt = Position([7, 9])
print(heuristic_dict[tuple(goal_pt)])
print(true_heuristic(start_pt, goal_pt))

@timeit
def do_astar():
    path = astar(grid, start_pt, goal_pt)
    return path



@timeit
def do_true_astar():
    path = astar(grid, start_pt, goal_pt, heuristic=true_heuristic)
    return path

path1 = do_astar()
path2 = do_true_astar()
print(path1)
print(path2)

# astar searched 50 cells
# 'do_astar' End. Took 0.803 ms
# astar searched 20 cells
# 'do_true_astar' End. Took 0.448 ms
# [(7, 2), (7, 3), (6, 3), (5, 3), (4, 3), (3, 3), (2, 3), (1, 3), (1, 4), (1, 5), (2, 5), (2, 6), (2, 7), (3, 7), (3, 8), (3, 9), (4, 9), (5, 9), (6, 9), (7, 9)]
# [(7, 2), (6, 2), (5, 2), (4, 2), (3, 2), (2, 2), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (5, 9), (6, 9), (7, 9)]