"""Unit tests for pathfinding."""
import unittest
from job import Job, JobId
from inventory_management_system.Order import OrderId
from inventory_management_system.Station import StationId
from inventory_management_system.Item import ItemId
from multiagent_planner.pathfinding import Position
from robot import RobotId

# python -m unittest

default_job_data = {
    'task_key': 'task:1',
    'station_id': StationId(1),
    'order_id': OrderId(2),
    'item_id': ItemId(3),
    'idx': 0,
    'robot_id': RobotId(1),
    'robot_start_pos': Position([0,1]),
    'item_zone': Position([1,2]),
    'station_zone': Position([3,4]),
    'robot_home': Position([5,6]),
}


class TestJob(unittest.TestCase):
    """Unit tests for jobs."""
    def test_new_job(self):
        """Validate creating new job"""
        job = Job(JobId(0), default_job_data)
        self.assertEqual(job.job_id, JobId(0))
        self.assertEqual(job.task_key, default_job_data['task_key'])
        self.assertEqual(job.station_id, default_job_data['station_id'])
        self.assertEqual(job.order_id, default_job_data['order_id'])
        self.assertEqual(job.item_id, default_job_data['item_id'])
        self.assertEqual(job.idx, default_job_data['idx'])
        self.assertEqual(job.robot_id, default_job_data['robot_id'])
        self.assertEqual(job.robot_start_pos, default_job_data['robot_start_pos'])
        self.assertEqual(job.item_zone, default_job_data['item_zone'])
        self.assertEqual(job.station_zone, default_job_data['station_zone'])
        self.assertEqual(job.robot_home, default_job_data['robot_home'])

        self.assertListEqual(job.path_robot_to_item, [])
        self.assertListEqual(job.path_item_to_station, [])
        self.assertListEqual(job.path_station_to_home, [])
        self.assertFalse(job.started)
        self.assertFalse(job.item_picked)
        self.assertFalse(job.going_to_station)
        self.assertFalse(job.item_dropped)
        self.assertFalse(job.returning_home)
        self.assertFalse(job.robot_returned)
        self.assertFalse(job.complete)
        self.assertFalse(job.error)