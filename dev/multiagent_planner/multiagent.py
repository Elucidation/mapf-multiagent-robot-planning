from multiagent_utils import get_scenario
import pathfinding
from visualizer import Visualizer

grid, goals, starts = get_scenario('scenarios/scenario4.yaml')

paths = pathfinding.MAPF1(grid, starts, goals, maxiter=100, T=40)
collisions = pathfinding.find_all_collisions(paths)
if not collisions:
    print('MAPF1 Found paths without collisions')
else:
    print(f'MAPF1 Collisions: {collisions}')

for i, path in enumerate(paths):
    print(f'Path {i} : {path}')

visualizer = Visualizer(grid, starts, goals, paths)
visualizer.show()
