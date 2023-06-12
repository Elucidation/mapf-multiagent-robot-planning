"""Unit tests for pathfinding."""
import logging
import unittest
from unittest.mock import Mock
from robot_allocator import RobotAllocator
from job import Job, JobId, JobState
from inventory_management_system.Order import OrderId
from inventory_management_system.Station import StationId
from inventory_management_system.Item import ItemId
from multiagent_planner.pathfinding import Position
from robot import Robot, RobotId, Path
from warehouses.warehouse_loader import WorldInfo
from world_db import WorldDatabaseManager
import numpy as np

mock_redis = Mock()

mock_logger = Mock()
# mock_logger.debug = print
# mock_logger.info = print
# mock_logger.warn = print
# mock_logger.error = print

mock_wdb = Mock(spec=WorldDatabaseManager)
mock_heuristic_builder = Mock()

# # Set return values for its methods
# mock_db_manager.get_timestamp.return_value = 1234567890
# mock_db_manager.get_dt_sec.return_value = 1.0
# mock_db_manager.get_robot.return_value = Robot(...)  # Replace with a suitable Robot object
# mock_db_manager.get_robots.return_value = [Robot(...), Robot(...)]  # Replace with suitable Robot objects

default_grid = np.zeros([5,5])
default_robots = [Robot(RobotId(0), Position((2,3))),Robot(RobotId(1), Position((3,4)))]
default_robot_home_zones = [Position((2,3)), Position((3,4))]
default_item_load_zones = [Position((1,0)), Position((1,1))]
default_station_zones = [Position((0,0)), Position((0,1))]

default_world = WorldInfo(default_grid, 
                          default_robot_home_zones,
                          default_item_load_zones,
                          default_station_zones)


class TestRobotAllocator(unittest.TestCase):
    """Unit tests for jobs."""
    def test_instantiate_robot_allocator(self):
        mock_redis.smembers.return_value = set()
        mock_wdb.get_robots.return_value = []
        robot_mgr = RobotAllocator(mock_logger, mock_redis, mock_wdb, default_world, mock_heuristic_builder)
        self.assertListEqual(robot_mgr.get_available_robots(), [])
    
    def test_instantiate_robot_allocator_with_robots(self):
        mock_redis.smembers.return_value = set()
        robots = default_robots.copy()
        mock_wdb.get_robots.return_value = robots
        robot_mgr = RobotAllocator(mock_logger, mock_redis, mock_wdb, default_world, mock_heuristic_builder)
        self.assertListEqual(robot_mgr.get_available_robots(), default_robots)
    
    def test_make_allocation(self):
        task_key = 'task:station:1:order:2:0:4'
        task_keys = set([task_key])
        mock_redis.smembers.return_value = task_keys
        robots = default_robots.copy()
        mock_wdb.get_robots.return_value = robots
        robot_mgr = RobotAllocator(mock_logger, mock_redis, mock_wdb, default_world, mock_heuristic_builder)
        
        mock_redis.lpop.return_value = task_key
        job = robot_mgr.assign_task_to_robot()
        self.assertIsNotNone(job)
        self.assertEqual(job.robot_id, default_robots[0].robot_id)
        self.assertEqual(job.task_key, task_key)
    
    def test_robot_no_pick_not_at_item_zone(self):
        task_key = 'task:station:1:order:2:0:4'
        task_keys = set([task_key])
        mock_redis.smembers.return_value = task_keys
        robots = default_robots.copy()
        mock_wdb.get_robots.return_value = robots
        robot_mgr = RobotAllocator(mock_logger, mock_redis, mock_wdb, default_world, mock_heuristic_builder)

        # Replace generate path with a mock
        robot_mgr.generate_path = Mock()
        robot_mgr.generate_path.return_value = Path([Position([1,2]), Position([2,2])])
        
        mock_redis.lpop.return_value = task_key
        job = robot_mgr.assign_task_to_robot()
        
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
        task_key = 'task:station:1:order:2:0:4'
        task_keys = set([task_key])
        mock_redis.smembers.return_value = task_keys
        robots = default_robots.copy()
        mock_wdb.get_robots.return_value = robots
        robot_mgr = RobotAllocator(mock_logger, mock_redis, mock_wdb, default_world, mock_heuristic_builder)

        # Replace generate path with a mock
        robot_mgr.generate_path = Mock()
        robot_mgr.generate_path.return_value = Path([Position([1,2]), Position([2,2])])
        
        mock_redis.lpop.return_value = task_key
        job = robot_mgr.assign_task_to_robot()
        
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