"""
DB interface class for world simulator to store world state in a Redis DB
"""
from typing import List
import functools
import json
import time
import redis
from warehouse_logger import create_warehouse_logger
from robot import Robot, RobotId, RobotStatus, Position

# Set up logging
logger = create_warehouse_logger("database_world_manager")


class WorldDatabaseManager:
    """DB Manager for world state"""

    def __init__(self, redis_con: redis.Redis):
        self.redis = redis_con
        self.robot_keys = self.redis.lrange('robots:all', 0, -1)
        logger.debug('Initialized WorldDatabaseManager instance')

    def reset(self):
        self.robot_keys = []
        self.delete_tables()

    def delete_tables(self):
        logger.warning('Resetting redis Robots/State')
        for key in self.redis.scan_iter("robot:*"):
            self.redis.delete(key)
        self.redis.delete('world:state', 'states', 'robots:all',
                          'robots:busy', 'robots:free')

    def add_robots(self, robots: List[Robot]):
        print('----')
        pipeline = self.redis.pipeline()
        for robot in robots:
            robot_key = f'robot:{robot.robot_id}'
            pipeline.hset(robot_key, mapping=robot.json_data())
            pipeline.rpush('robots:all', robot_key)
            pipeline.sadd('robots:free', robot_key)
            # Add robots as free initially
        pipeline.execute()
        self.robot_keys = self.redis.lrange('robots:all', 0, -1)

    def get_timestamp(self) -> int:
        return int(self.redis.hget('states', 'timestamp'))

    def update_timestamp(self, t: int):
        return self.redis.hset('states', 'timestamp', t)

    def set_dt_sec(self, dt_sec: float):
        return self.redis.hset('states', 'dt_sec', dt_sec)

    def get_dt_sec(self) -> float:
        return float(self.redis.hget('states', 'dt_sec'))

    def set_robot_path(self, robot_id: int, path: list):
        robot_key = f'robot:{robot_id}'
        return self.redis.hset(robot_key, 'path', json.dumps(path))

    def update_robots(self, robots: List[Robot],
                      robots_json_data: List[str] = None, pipeline: 'redis.Pipeline' = None):
        # Execute update if pipeline not defined, else pass to pipeline.
        _pipeline = self.redis.pipeline() if pipeline is None else pipeline
        for idx, robot in enumerate(robots):
            robot_key = f'robot:{robot.robot_id}'
            if robots_json_data:
                _pipeline.hset(robot_key, mapping=robots_json_data[idx])
            else:
                _pipeline.hset(robot_key, mapping=robot.json_data())
            # Add robot to busy/free based on state
            if robot.state == RobotStatus.AVAILABLE:
                _pipeline.sadd('robots:free', robot_key)
                _pipeline.srem('robots:busy', robot_key)
            elif robot.state == RobotStatus.IN_PROGRESS:
                _pipeline.sadd('robots:busy', robot_key)
                _pipeline.srem('robots:free', robot_key)
        if pipeline is None:
            _pipeline.execute()

    def _parse_position(self, position_str: str) -> Position:
        pos_x, pos_y = json.loads(position_str)
        return (pos_x, pos_y)  # (x, y) for Robot

    def _parse_path(self, path_str: str) -> List[Position]:
        # Note: invalid path str will fail out on loads.
        path = json.loads(path_str)
        return [Position(x, y) for x, y in path]  # Create position tuples

    def get_robot(self, robot_id: RobotId) -> Robot:
        robot_key = f'robot:{robot_id}'
        json_data = self.redis.hgetall(robot_key)
        return Robot.from_json(json_data)

    def get_robots(self) -> List[Robot]:
        pipeline = self.redis.pipeline()
        for robot_key in self.robot_keys:
            pipeline.hgetall(robot_key)
        robots_json_data = pipeline.execute()
        return [Robot.from_json(json_data) for json_data in robots_json_data]

    def log_world_state(self, data: dict):
        """Add latest world state data to the stream."""
        self.redis.xadd('world:state', data, maxlen=100, approximate=True)