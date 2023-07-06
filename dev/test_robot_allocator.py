"""Unit tests for pathfinding."""
import logging
import time
import unittest
from unittest import mock
from unittest.mock import Mock
import numpy as np
from robot_allocator import RobotAllocator
from job import JobState
from multiagent_planner.pathfinding import Position
from robot import Robot, RobotId, Path
from warehouses.warehouse_loader import WorldInfo
from world_db import WorldDatabaseManager

mock_redis = Mock()

# logger = Mock()
# logger.debug = print
# logger.info = print
# logger.warn = print
# logger.warning = print
# logger.error = print
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)
logger.addHandler(handler)

mock_wdb = Mock(spec=WorldDatabaseManager)
mock_heuristic = Mock()
mock_heuristic.__name__ = 'Mock Heuristic'

default_grid = np.zeros([5, 5])
default_robot_home_zones = [Position((2, 3)), Position((3, 4))]
default_item_load_zones = [Position((1, 0)), Position((1, 1))]
default_station_zones = [Position((0, 0)), Position((0, 1))]

default_world = WorldInfo(default_grid,
                          default_robot_home_zones,
                          default_item_load_zones,
                          default_station_zones)


class TestRobotAllocator(unittest.TestCase):
    """Unit tests for jobs."""

    def test_instantiate_robot_allocator(self):
        mock_redis.smembers.return_value = set()
        mock_wdb.get_robots.return_value = []
        mock_redis.xread.return_value = None
        robot_mgr = RobotAllocator(
            logger, mock_redis, mock_wdb, default_world, mock_heuristic)
        self.assertListEqual(robot_mgr.get_available_robots(), [])

    def test_instantiate_robot_allocator_with_robots(self):
        mock_redis.smembers.return_value = set()
        robots = [Robot(RobotId(0), Position((2, 3))),
                  Robot(RobotId(1), Position((3, 4)))]
        mock_wdb.get_robots.return_value = robots
        mock_redis.xread.return_value = None
        robot_mgr = RobotAllocator(
            logger, mock_redis, mock_wdb, default_world, mock_heuristic)
        self.assertListEqual(robot_mgr.get_available_robots(), robots)

    def test_find_and_assign_task_to_robot(self):
        task_key = 'task:station:1:order:2:0:4'
        task_keys = set([task_key])
        mock_redis.smembers.return_value = task_keys
        robots = [Robot(RobotId(0), Position((2, 3))),
                  Robot(RobotId(1), Position((3, 4)))]
        mock_wdb.get_robots.return_value = robots
        mock_redis.xread.return_value = None
        robot_mgr = RobotAllocator(
            logger, mock_redis, mock_wdb, default_world, mock_heuristic)

        mock_redis.lpop.return_value = task_key
        job = robot_mgr.find_and_assign_task_to_robot()
        self.assertIsNotNone(job)
        self.assertEqual(job.robot_id, robots[0].robot_id)
        self.assertEqual(job.task_key, task_key)

    def test_robot_no_pick_not_at_item_zone(self):
        task_key = 'task:station:1:order:2:0:4'
        task_keys = set([task_key])
        mock_redis.smembers.return_value = task_keys
        mock_redis.xread.return_value = None
        robots = [Robot(RobotId(0), Position((2, 3))),
                  Robot(RobotId(1), Position((3, 4)))]
        mock_wdb.get_robots.return_value = robots
        mock_redis.xread.return_value = None
        robot_mgr = RobotAllocator(
            logger, mock_redis, mock_wdb, default_world, mock_heuristic)

        # Replace generate path with a mock
        robot_mgr.generate_path = Mock(return_value=Path(
            [Position([1, 2]), Position([2, 2])]))

        # Assign task to first robot manually
        job = robot_mgr.assign_task_to_robot(task_key, robots[0])

        # Expect it to go through states
        expected_state = JobState.WAITING_TO_START
        self.assertEqual(job.state, expected_state)
        self.assertTrue(robot_mgr.check_and_update_job(job))

        expected_state = JobState.PICKING_ITEM
        self.assertEqual(job.state, expected_state)

        # Try pick but should not happen because robot still not there
        self.assertFalse(robot_mgr.check_and_update_job(job))

        # Move robot to item zone 0
        robots[0].pos = default_item_load_zones[0]
        self.assertTrue(robot_mgr.check_and_update_job(job))

    def test_allocate_full_good_cycle_job(self):
        """Expect job going through full cycle."""
        task_key = 'task:station:1:order:2:0:4'
        task_keys = set([task_key])
        mock_redis.smembers.return_value = task_keys
        robots = [Robot(RobotId(0), Position((2, 3))),
                  Robot(RobotId(1), Position((3, 4)))]
        mock_wdb.get_robots.return_value = robots
        mock_redis.xread.return_value = None
        robot_mgr = RobotAllocator(
            logger, mock_redis, mock_wdb, default_world, mock_heuristic)

        # Replace generate path with a mock
        robot_mgr.generate_path = Mock(return_value=Path(
            [Position([1, 2]), Position([2, 2])]))

        # Manually assign task to robot
        job = robot_mgr.assign_task_to_robot(task_key, robots[0])

        # Expect it to go through states in sequence
        expected_state = JobState.WAITING_TO_START
        self.assertEqual(job.state, expected_state)

        # Expect go to pick item from item zone
        self.assertTrue(robot_mgr.check_and_update_job(job))
        expected_state = JobState.PICKING_ITEM
        self.assertEqual(job.state, expected_state)

        # Move robot to item zone
        robots[0].pos = default_item_load_zones[0]
        # Expect pick item at item zone
        self.assertTrue(robot_mgr.check_and_update_job(job))
        expected_state = JobState.ITEM_PICKED
        self.assertEqual(job.state, expected_state)

        self.assertTrue(robot_mgr.check_and_update_job(job))
        # Expect take item to station
        expected_state = JobState.GOING_TO_STATION
        self.assertEqual(job.state, expected_state)

        # Move robot to station zone
        robots[0].pos = default_station_zones[0]
        # Expect drop item at station
        self.assertTrue(robot_mgr.check_and_update_job(job))
        expected_state = JobState.ITEM_DROPPED
        self.assertEqual(job.state, expected_state)

        # Expect going home
        self.assertTrue(robot_mgr.check_and_update_job(job))
        expected_state = JobState.RETURNING_HOME
        self.assertEqual(job.state, expected_state)

        # Move robot home
        robots[0].pos = default_robot_home_zones[0]
        # Finish job
        self.assertTrue(robot_mgr.check_and_update_job(job))
        expected_state = JobState.COMPLETE
        self.assertEqual(job.state, expected_state)

        # Expect False return if trying to update a completed job
        self.assertFalse(robot_mgr.check_and_update_job(job))

    def test_update_good(self):
        """Expect normal update assigns a task to robot"""
        task_key = 'task:station:1:order:2:0:4'
        task_keys = set([task_key])
        mock_redis.smembers.return_value = task_keys
        mock_redis.xread.return_value = None
        robots = [Robot(RobotId(0), Position((2, 3))),
                  Robot(RobotId(1), Position((3, 4)))]
        mock_wdb.get_robots.return_value = robots
        robot_mgr = RobotAllocator(
            logger, mock_redis, mock_wdb, default_world, mock_heuristic)

        # Replace generate path with a mock
        robot_mgr.generate_path = Mock(return_value=Path(
            [Position([1, 2]), Position([2, 2])]))

        pipeline = mock_redis.pipeline.return_value
        pipeline.execute.return_value = [1,[task_key]]
        robot_mgr.update(robots, t_start=0, time_left=1)
        # Expect one job assigned, for the first robot and only task
        robot = robots[0]
        self.assertEqual(len(robot_mgr.jobs), 1)
        self.assertEqual(robot_mgr.jobs[0].robot_id, robot.robot_id)
        self.assertEqual(robot_mgr.jobs[0].task_key, task_key)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.WAITING_TO_START)

        # After first update, no more new task keys available
        pipeline.execute.return_value = [0,[]]
        # No more tasks, now expect job to update
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.PICKING_ITEM)

        # Expect still picking state while robot not in zone
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.PICKING_ITEM)
        self.assertIsNone(robot.held_item_id)

        # Move robot to item zone, now expect state transition
        robot.pos = robot_mgr.jobs[0].item_zone
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.ITEM_PICKED)
        self.assertIsNotNone(robot.held_item_id)

        # Expect transition
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.GOING_TO_STATION)

        # Expect still going to station since not there
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.GOING_TO_STATION)

        # Expect transition since at station
        robot.pos = robot_mgr.jobs[0].station_zone
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.ITEM_DROPPED)
        self.assertIsNone(robot.held_item_id)

        # Expect transition
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.RETURNING_HOME)

        # Expect no transition till home
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.RETURNING_HOME)

        # Expect job complete and removed
        robot.pos = robot_mgr.jobs[0].robot_home
        robot_mgr.update(robots, t_start=0, time_left=1)
        # Note: Allocations not yet managed
        self.assertIsNone(robot_mgr.allocations[robot.robot_id])
        self.assertEqual(len(robot_mgr.jobs), 0)

        # Expect no change on next update
        robot_mgr.update(robots, t_start=0, time_left=1)
        self.assertIsNone(robot_mgr.allocations[robot.robot_id])
        self.assertEqual(len(robot_mgr.jobs), 0)

    def test_allocate_revert_too_long(self):
        """Expect assigns a task to robot, too-long update reverts change"""

        task_key = 'task:station:1:order:2:0:4'
        task_keys = set([task_key])
        mock_redis.smembers.return_value = task_keys
        robots = [Robot(RobotId(0), Position((2, 3))),
                  Robot(RobotId(1), Position((3, 4)))]
        mock_wdb.get_robots.return_value = robots
        mock_redis.xread.return_value = None
        robot_mgr = RobotAllocator(
            logger, mock_redis, mock_wdb, default_world, mock_heuristic)

        # Replace generate path with a mock
        robot_mgr.generate_path = Mock(return_value=Path(
            [Position([1, 2]), Position([2, 2])]))

        # redis lpop tasks returns task_key once, then None thereafter
        # mock_redis.lpop.side_effect = itertools.chain([task_key], itertools.cycle([None]))
        pipeline = mock_redis.pipeline.return_value
        pipeline.execute.return_value = [1,[task_key]]

        # TODO : If on first update before any job created, after creating a job but before finishing
        # the update, if time runs over, expect revert new jobs and task calls.
        MAX_UPDATE_TIME_SEC = 0.5
        with mock.patch('time.perf_counter') as mock_perf_counter:
            mock_perf_counter.return_value = MAX_UPDATE_TIME_SEC+0.00001  # Just over threshold
            robot_mgr.update(robots, t_start=0, time_left=MAX_UPDATE_TIME_SEC)

        # Update once. Expect one job assigned, for the first robot and only task
        robot_mgr.update(robots, t_start=0, time_left=1)
        robot = robots[0]
        self.assertEqual(len(robot_mgr.jobs), 1)
        self.assertEqual(robot_mgr.jobs[0].robot_id, robot.robot_id)
        self.assertEqual(robot_mgr.jobs[0].task_key, task_key)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.WAITING_TO_START)
        self.assertIsNone(robot_mgr.allocations[robot.robot_id])

        # After first update, no more new task keys available
        pipeline.execute.return_value = [0,[]]
        # No more tasks, now expect job with passed too-long update will cause no changes
        robot_mgr.update(robots, t_start=time.perf_counter() - MAX_UPDATE_TIME_SEC, time_left=MAX_UPDATE_TIME_SEC)
        self.assertEqual(robot_mgr.jobs[0].state, JobState.WAITING_TO_START)
