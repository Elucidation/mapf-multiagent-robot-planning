"""Script to run multiagent sim and visualize it."""
import numpy as np
import yaml

def get_scenario(filename: str) -> tuple[np.ndarray, list[tuple[int, int]], list[tuple[int, int]]]:
    with open(filename, 'r', encoding='utf8') as filestream:
        scenario = yaml.safe_load(filestream)
    # pylint: disable=redefined-outer-name
    grid = np.array(scenario['grid'])
    goals = [(int(r), int(c)) for (r, c) in scenario['goals']]
    starts = [(int(r), int(c)) for (r, c) in scenario['starts']]
    return grid, goals, starts


if __name__ == '__main__':
    from .visualizer import Visualizer
    from . import pathfinding
    grid, goals, starts = get_scenario(
        'multiagent_planner/scenarios/scenario5.yaml')
    
    paths = pathfinding.mapf1(grid, starts, goals, maxiter=100, max_time=40)
    collisions = pathfinding.find_all_collisions(paths)
    if not collisions:
        print('MAPF1 Found paths without collisions')
    else:
        print(f'MAPF1 Collisions: {collisions}')

    # for i, path in enumerate(paths):
    #     print(f'Path {i} : {path}')

    paths = pathfinding.mapf2(grid, starts, goals, maxiter=100, max_time=40)
    collisions = pathfinding.find_all_collisions(paths)
    if not collisions:
        print('MAPF2 Found paths without collisions')
    else:
        print(f'MAPF2 Collisions: {collisions}')

    # for i, path in enumerate(paths):
    #     print(f'Path {i} : {path}')

    visualizer = Visualizer(grid, starts, goals, paths)
    visualizer.show()
