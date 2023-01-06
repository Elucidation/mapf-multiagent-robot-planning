import unittest
from pathfinding import *


class TestPathfinding(unittest.TestCase):
    def test_find_collisions(self):
        p1 = [(0, 0), (0, 1), (0, 1), (0, 2)]
        p2 = [(1, 0), (1, 1), (0, 1), (0, 0)]
        # These collide at vertex at time 2
        collisions = find_collisions(p1, p2)
        self.assertEqual(collisions, [[1, 0, 1, 2]])

    def test_MAPF0(self):
        grid, goals, starts = get_scenario('scenarios/scenario2.yaml')
        paths = MAPF0(grid, starts, goals)
        collisions = find_all_collisions(paths)
        self.assertEqual(collisions, [[2, 2, 5, 6]])

    def test_MAPF1(self):
        grid, goals, starts = get_scenario('scenarios/scenario3.yaml')
        paths = MAPF1(grid, starts, goals, maxiter=100)
        collisions = find_all_collisions(paths)
        self.assertEqual(collisions, [])

    def test_single_robot_astar(self):
        grid, goals, starts = get_scenario('scenarios/scenario1.yaml')
        path = astar(grid, starts[0], goals[0])
        expected_path = [(1, 4), (1, 3), (1, 2), (1, 1), (2, 1),
                         (3, 1), (4, 1), (4, 2), (4, 3), (3, 3), (3, 4)]
        self.assertEqual(path, expected_path)


if __name__ == '__main__':
    unittest.main()
