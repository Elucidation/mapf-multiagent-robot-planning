# This folder provides a function for generating an optimal heuristic table for a given grid
# optimal as in A* shortest path from any open cell to any other open cell
from collections import deque
import functools
import pickle
import os
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
def get_distances(grid, start: Position, dtype=int):
    # start is [row, col] of grid (2d array, 0 is open, 1 is wall)
    # We will use a special value to represent inaccessible areas
    SPECIAL = -1
    distances = np.full_like(grid, fill_value=SPECIAL, dtype=dtype)

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
            # If valid cell, grid is empty and hasn't been set in distances yet, replace it
            if ((0 <= new_x < grid.shape[0]) and (0 <= new_y < grid.shape[1]) and
                    grid[new_x, new_y] == 0 and distances[new_x, new_y] == SPECIAL):
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
    true_heuristic_dict_for_grid = {Position(pos): get_distances(grid, pos) for pos in positions}
    return true_heuristic_dict_for_grid

def write_heuristic_to_file(filename: str, heuristic: dict):
    with open(filename, 'wb') as f:
        pickle.dump(heuristic, f)

def load_heuristic_from_file(filename: str):
    with open(filename, 'rb') as f:
        _dict = pickle.load(f)    
    return _dict

def load_heuristic(warehouse_yaml: str, world_info: 'WorldInfo', logger: str) -> tuple['WorldInfo', dict]:
    """Tries to load heuristic dict from file, else builds and saves it. Returns the dict"""
    filename = f'{os.path.splitext(warehouse_yaml)[0]}_heuristic.pkl'
    if os.path.exists(filename):
        logger.info(f'Found existing heuristic for {warehouse_yaml} -> {filename}, loading')
        t_start = time.perf_counter()
        _dict = load_heuristic_from_file(filename)
        logger.info(f'Loaded true heuristic grid in {(time.perf_counter() - t_start)*1000:.2f} ms')
    else:
        # Build true heuristic function
        t_start = time.perf_counter()
        logger.info(f'Building true heuristic for {warehouse_yaml}')
        # Build true heuristic grid
        _dict = build_true_heuristic(world_info.world_grid, world_info.get_all_zones())
        logger.info(f'Built true heuristic grid in {(time.perf_counter() - t_start)*1000:.2f} ms')
        write_heuristic_to_file(filename, _dict)
    return _dict

if __name__ == '__main__':
    from warehouses.warehouse_loader import WorldInfo
    import os
    # Load world info from yaml
    warehouse_yaml = os.getenv('WAREHOUSE_YAML', 'warehouses/main_warehouse.yaml')
    
    heuristic_filename = f'{os.path.splitext(warehouse_yaml)[0]}_heuristic.pkl'

    world_info = WorldInfo.from_yaml(warehouse_yaml)
    print(
        f'World Shape: {world_info.world_grid.shape}, {len(world_info.robot_home_zones)} robots,'
        f' {len(world_info.item_load_zones)} item zones, {len(world_info.station_zones)} stations')

    if os.path.exists(heuristic_filename):
        print(f'Found existing heuristic for {warehouse_yaml} -> {heuristic_filename}, loading')
        t_start = time.perf_counter()
        true_heuristic_dict = load_heuristic_from_file(heuristic_filename)
        print(f'Loaded true heuristic grid in {(time.perf_counter() - t_start)*1000:.2f} ms')
    else:
        # Build true heuristic function
        t_start = time.perf_counter()
        print(f'Building true heuristic for {warehouse_yaml}')
        # Build true heuristic grid
        true_heuristic_dict = build_true_heuristic(world_info.world_grid, world_info.get_all_zones())
        print(f'Built true heuristic grid in {(time.perf_counter() - t_start)*1000:.2f} ms')
        write_heuristic_to_file(heuristic_filename, true_heuristic_dict)

    # def show_size_stats():
    #     entry: np.ndarray = next(iter(true_heuristic_dict.values()))
    #     print(f'Dict with {len(true_heuristic_dict)} keys, ')
    #     byte_size_dict = sum([(sys.getsizeof(key) + value.nbytes) for key, value in true_heuristic_dict.items()])
    #     print(f'Size: {byte_size_dict:,} bytes, one entry: {entry.nbytes} dtype = {entry.dtype}')
    #     N, M = world_info.world_grid.shape
    #     expected_size = N*M*len(true_heuristic_dict)
    #     print(f'NxM = {N}x{M} = {N*M}')
    #     print(f'Expected size ~NxMxZ = {N}x{M}x{len(true_heuristic_dict)} = {expected_size:,} values')
    #     print(f'For {entry.dtype} = {entry.itemsize} bytes, so {entry.itemsize} bytes * {expected_size:,} = {entry.itemsize*expected_size:,} bytes')
    #     expected_bytes = entry.itemsize*expected_size
    #     measured_bytes = byte_size_dict
    #     print(f'Measured {measured_bytes} vs {expected_bytes}, diff = {measured_bytes / expected_bytes * 100 : .2f} %')

    # def test_heuristic_grid_perf():
    #     print('---')
    #     import random
    #     random.seed(123)
    #     K = 1000000
    #     valid_starts = [Position(row) for row in np.argwhere(world_info.world_grid == 0)]
    #     valid_goals = world_info.get_all_zones()
    #     starts = [random.choice(valid_starts) for _ in range(K)]
    #     goals = [random.choice(valid_goals) for _ in range(K)]
    #     print(f'Testing true heuristic grid on {K} queries')
    #     t_start = time.perf_counter()
    #     for i in range(K):
    #         pos_a = starts[i]
    #         pos_b = goals[i]
    #         dist = true_heuristic_dict[pos_b][pos_a]
    #     t_end = time.perf_counter()
    #     print(f'Did {K:,} queries into true heuristic grid in {(t_end - t_start)*1000:.2f} ms',)
    #     # Did 1,000,000 queries into true heuristic grid in 306.90 ms
    
    # def test_pickle_heuristic():
    #     import pickle
    #     filename = 'true_heuristic_dict.pkl'
    #     t_start = time.perf_counter()
    #     with open(filename, 'wb') as f:
    #         pickle.dump(true_heuristic_dict, f)
    #     t_end = time.perf_counter()
        
    #     byte_size_dict = sum([(sys.getsizeof(key) + value.nbytes) for key, value in true_heuristic_dict.items()])
    #     print(f'Saved true heuristic {byte_size_dict/1024:,.1f} kb  to {filename} in {(t_end - t_start)*1000:.2f} ms')
    #     # Saved true heuristic 289.1 kb  to true_heuristic_dict.pkl in 2.5 ms
    #     # 292kb on disk

    #     for i in range(3):
    #         t_start = time.perf_counter()
    #         with open(filename, 'rb') as f:
    #             read_dict = pickle.load(f)
    #         t_end = time.perf_counter()
    #         read_dict_size = sum([(sys.getsizeof(key) + value.nbytes) for key, value in read_dict.items()])
    #         print(f'Loaded dict {read_dict_size/1024:,.1f} kb  from {filename} in {(t_end - t_start)*1000:.2f} ms')
    #     # Loaded dict 289.1 kb  from true_heuristic_dict.pkl in 5.60 ms, < 2ms after that

    #     assert(read_dict.keys() == true_heuristic_dict.keys())
    #     for key in true_heuristic_dict.keys():
    #         assert((true_heuristic_dict[key] == read_dict[key]).all())
        