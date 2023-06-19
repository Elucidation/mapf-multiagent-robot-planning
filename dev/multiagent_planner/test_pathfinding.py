"""Unit tests for pathfinding."""
import unittest
import numpy as np
from .pathfinding import Position
# from .pathfinding_heuristic import timeit
from . import pathfinding
from . import pathfinding_heuristic as pfh
from .multiagent import get_scenario
# python -m unittest


class TestPathfinding(unittest.TestCase):
    """Unit tests for pathfinding module"""

    def test_find_collisions(self):
        path1 = [(0, 0), (0, 1), (0, 1), (0, 2)]
        path2 = [(1, 0), (1, 1), (0, 1), (0, 0)]
        # These collide at vertex at time 2
        collisions = pathfinding.find_collisions(path1, path2)
        self.assertEqual(collisions, [(1, 0, 1, 2)])

    def test_mapf0(self):
        grid, goals, starts = get_scenario(
            'multiagent_planner/scenarios/scenario2.yaml')
        paths = pathfinding.mapf0(grid, starts, goals)
        collisions = pathfinding.find_all_collisions(paths)
        self.assertEqual(collisions, [(2, 2, 5, 6)])

    def test_mapf1(self):
        grid, goals, starts = get_scenario(
            'multiagent_planner/scenarios/scenario3.yaml')
        paths = pathfinding.mapf1(grid, starts, goals, maxiter=100)
        collisions = pathfinding.find_all_collisions(paths)
        self.assertEqual(collisions, [])

    def test_single_robot_astar(self):
        grid, goals, starts = get_scenario(
            'multiagent_planner/scenarios/scenario1.yaml')
        path = pathfinding.astar(grid, starts[0], goals[0])
        expected_path = [(1, 4), (1, 3), (1, 2), (1, 1), (2, 1),
                         (3, 1), (4, 1), (4, 2), (4, 3), (3, 3), (3, 4)]
        self.assertEqual(path, expected_path)

    def test_st_astar_no_obstacles(self):
        grid, goals, starts = get_scenario(
            'multiagent_planner/scenarios/scenario1.yaml')
        dynamic_obstacles = set()
        # End as soon as we reach position
        path = pathfinding.st_astar(
            grid, starts[0], goals[0], dynamic_obstacles, end_fast=True)
        expected_path = [(1, 4), (1, 3), (1, 2), (1, 1), (2, 1),
                         (3, 1), (4, 1), (4, 2), (4, 3), (3, 3), (3, 4)]
        self.assertEqual(path, expected_path)

        # Without end_fast
        path = pathfinding.st_astar(
            grid, starts[0], goals[0], dynamic_obstacles, max_time=12)
        expected_path = [(1, 4), (1, 3), (1, 2), (1, 1), (2, 1),
                         (3, 1), (4, 1), (4, 2), (4, 3), (3, 3), (3, 4), (3, 4), (3, 4)]
        self.assertEqual(path, expected_path)

        # With offset start_time no change
        path = pathfinding.st_astar(
            grid, starts[0], goals[0], dynamic_obstacles, t_start=123, end_fast=True)
        expected_path = [(1, 4), (1, 3), (1, 2), (1, 1), (2, 1),
                         (3, 1), (4, 1), (4, 2), (4, 3), (3, 3), (3, 4)]
        self.assertEqual(path, expected_path)

    def test_st_astar_with_static_obstacles(self):
        grid, goals, starts = get_scenario(
            'multiagent_planner/scenarios/scenario3.yaml')
        dynamic_obstacles = set()
        static_obstacles = set([(2, 8)])

        path_no_static = pathfinding.st_astar(
            grid, starts[0], goals[0], dynamic_obstacles, static_obstacles=set(), end_fast=True)
        # - [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        # - [1, S, x, x, x, x, 0, 0, 0, 0, 1]
        # - [1, 0, 0, 0, 0, x, x, x, x, 0, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, x, 0, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, x, 0, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, F, 0, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1]
        # - [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        # - [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        # - [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        expected_path_no_static = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5),
                                   (2, 5), (2, 6), (2, 7), (2, 8), (3, 8), (4, 8), (5, 8)]
        self.assertEqual(path_no_static, expected_path_no_static)
        
        path_static = pathfinding.st_astar(
            grid, starts[0], goals[0], dynamic_obstacles, static_obstacles, end_fast=True)
        # - [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        # - [1, S, x, x, x, x, 0, x, x, x, 1]
        # - [1, 0, 0, 0, 0, x, x, x, B, x, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, 0, x, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, x, x, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, F, 0, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1]
        # - [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1]
        # - [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        # - [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        # - [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        expected_path_static = [
            (1, 1), (1, 2), (1, 3), (1, 4),
            (1, 5), (2, 5), (2, 6), (2, 7), (1, 7),
            (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8), (5, 8)]
        self.assertEqual(path_static, expected_path_static)
    
    def test_true_heuristic_1(self):
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
        heuristic_dict = pfh.build_true_heuristic(grid)
        def true_heuristic(pos_a: Position, pos_b: Position) -> float:
            return float(heuristic_dict[pos_b][pos_a])

        start_pt = Position([7, 2])
        goal_pt = Position([7, 9])
        # print(heuristic_dict[tuple(goal_pt)])
        # [[-1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1]
        # [-1 14 13 12 11 10  9  8  7  6 -1]
        # [-1 15 14 13 -1  9  8  7  6  5 -1]
        # [-1 16 15 14 -1 -1 -1  6  5  4 -1]
        # [-1 17 16 15 -1 27 -1 -1 -1  3 -1]
        # [-1 18 17 16 -1 26 27 28 -1  2 -1]
        # [-1 19 18 17 -1 25 26 27 -1  1 -1]
        # [-1 20 19 18 -1 24 25 26 -1  0 -1]
        # [-1 21 20 19 -1 23 24 25 -1  1 -1]
        # [-1 22 21 20 21 22 23 24 -1  2 -1]
        # [-1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1]]
        # print(true_heuristic(start_pt, goal_pt)) -> 19.0

        # @timeit
        def do_astar():
            path = pathfinding.astar(grid, start_pt, goal_pt)
            return path



        # @timeit
        def do_true_astar():
            path = pathfinding.astar(grid, start_pt, goal_pt, heuristic=true_heuristic)
            return path

        path1 = do_astar()
        path2 = do_true_astar()
        # print(path1)
        # print(path2)
        self.assertListEqual(path1, [(7, 2), (7, 3), (6, 3), (5, 3), (4, 3), (3, 3), (2, 3), (1, 3), (1, 4), (1, 5), (2, 5), (2, 6), (2, 7), (3, 7), (3, 8), (3, 9), (4, 9), (5, 9), (6, 9), (7, 9)])
        self.assertListEqual(path2, [(7, 2), (6, 2), (5, 2), (4, 2), (3, 2), (2, 2), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (5, 9), (6, 9), (7, 9)])

        # astar searched 50 cells
        # 'do_astar' End. Took 0.803 ms
        # astar searched 20 cells
        # 'do_true_astar' End. Took 0.448 ms
        # [(7, 2), (7, 3), (6, 3), (5, 3), (4, 3), (3, 3), (2, 3), (1, 3), (1, 4), (1, 5), (2, 5), (2, 6), (2, 7), (3, 7), (3, 8), (3, 9), (4, 9), (5, 9), (6, 9), (7, 9)]
        # [(7, 2), (6, 2), (5, 2), (4, 2), (3, 2), (2, 2), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (5, 9), (6, 9), (7, 9)]
        


if __name__ == '__main__':
    unittest.main()
