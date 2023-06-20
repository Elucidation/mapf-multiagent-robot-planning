# This folder provides a function for generating an optimal heuristic table for a given grid
# optimal as in A* shortest path from any open cell to any other open cell
from collections import deque
import functools
import time
import numpy as np
from .pathfinding import Position


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
def get_distances(grid, start: Position, dtype=np.int8):
    # start is [row, col] of grid (2d array, 0 is open, 1 is wall)
    # We will use -1 to represent inaccessible areas
    distances = -np.ones_like(grid, dtype=dtype)

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
            if ((0 <= new_x < grid.shape[0]) and (0 <= new_y < grid.shape[1]) and
                    grid[new_x, new_y] == 0 and distances[new_x, new_y] == -1):
                distances[new_x, new_y] = distances[current[0], current[1]] + 1
                queue.append((new_x, new_y))
    return distances

# @timeit
def build_true_heuristic(grid, positions: list[Position]):
    """
    Builds a heuristic dict keyed for all given positions
    heuristic_dict[pos] = 2D np grid with each cell containing integer distance to it from pos
    Impassable cells are -1 score
    """
    true_heuristic_dict_for_grid = {}
    for pos in positions:
        true_heuristic_dict_for_grid[tuple(pos)] = get_distances(grid, pos)
    return true_heuristic_dict_for_grid


if __name__ == '__main__':
    from warehouses.warehouse_loader import WorldInfo
    import os
    import sys
    # Load world info from yaml
    world_info = WorldInfo.from_yaml(
        os.getenv('WAREHOUSE_YAML', 'warehouses/main_warehouse.yaml'))
    print(
        f'World Shape: {world_info.world_grid.shape}, {len(world_info.robot_home_zones)} robots,'
        f' {len(world_info.item_load_zones)} item zones, {len(world_info.station_zones)} stations')

    # Build true heuristic function
    t_start = time.perf_counter()
    print('Building true heuristic')
    # Build true heuristic grid
    true_heuristic_dict = build_true_heuristic(world_info.world_grid, world_info.get_all_zones())
    print(f'Built true heuristic grid in {(time.perf_counter() - t_start)*1000:.2f} ms',)
    entry: np.ndarray = next(iter(true_heuristic_dict.values()))
    print(f'Dict with {len(true_heuristic_dict)} keys, ')
    byte_size_dict = sum([(sys.getsizeof(key) + value.nbytes) for key, value in true_heuristic_dict.items()])
    print(f'Size: {byte_size_dict:,} bytes, one entry: {entry.nbytes} dtype = {entry.dtype}')
    N, M = world_info.world_grid.shape
    expected_size = N*M*len(true_heuristic_dict)
    print(f'NxM = {N}x{M} = {N*M}')
    print(f'Expected size ~NxMxZ = {N}x{M}x{len(true_heuristic_dict)} = {expected_size:,} values')
    print(f'For {entry.dtype} = {entry.itemsize} bytes, so {entry.itemsize} bytes * {expected_size:,} = {entry.itemsize*expected_size:,} bytes')
    expected_bytes = entry.itemsize*expected_size
    measured_bytes = byte_size_dict
    print(f'Measured {measured_bytes} vs {expected_bytes}, diff = {measured_bytes / expected_bytes * 100 : .2f} %')