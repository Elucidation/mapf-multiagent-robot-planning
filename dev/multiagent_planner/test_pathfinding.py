"""Unit tests for pathfinding."""
import unittest
from . import pathfinding
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


if __name__ == '__main__':
    unittest.main()
