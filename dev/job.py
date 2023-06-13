"""Job class for tracking Robot-Task allocations"""

from enum import Enum
from typing import NewType
from inventory_management_system.Order import OrderId
from inventory_management_system.Station import StationId
from inventory_management_system.Item import ItemId
from multiagent_planner.pathfinding import Position, Path
from robot import RobotId

JobId = NewType('JobId', int)


class JobState(Enum):
    """Track state of a job."""
    WAITING_TO_START = 1
    PICKING_ITEM = 2
    ITEM_PICKED = 3
    GOING_TO_STATION = 4
    ITEM_DROPPED = 5
    RETURNING_HOME = 6
    COMPLETE = 7

    ERROR = -1


class Job:
    "Build a job from a task-robot allocation, containing job positions/paths and state."

    def __init__(self, job_id: JobId, job_data: dict) -> None:
        self.job_id = job_id
        self.task_key: str = job_data['task_key']
        self.station_id: StationId = job_data['station_id']
        self.order_id: OrderId = job_data['order_id']
        self.item_id: ItemId = job_data['item_id']
        self.idx: int = job_data['idx']
        self.robot_id: RobotId = job_data['robot_id']
        # Stops on route
        self.robot_start_pos: Position = job_data['robot_start_pos']
        self.item_zone: Position = job_data['item_zone']
        self.station_zone: Position = job_data['station_zone']
        self.robot_home: Position = job_data['robot_home']

        # Paths
        self.path_robot_to_item: Path = []
        self.path_item_to_station: Path = []
        self.path_station_to_home: Path = []

        # Initialize state
        self.state = JobState.WAITING_TO_START

    def copy(self):
        """Return a new copy of this job"""
        job_data = {
            'task_key': self.task_key,
            'station_id': self.station_id,
            'order_id': self.order_id,
            'item_id': self.item_id,
            'idx': self.idx,
            'robot_id': self.robot_id,
            'robot_start_pos': self.robot_start_pos,
            'item_zone': self.item_zone,
            'station_zone': self.station_zone,
            'robot_home': self.robot_home
        }
        new_job = Job(self.job_id, job_data)
        new_job.state = self.state
        new_job.path_robot_to_item = self.path_robot_to_item.copy()
        new_job.path_item_to_station = self.path_item_to_station.copy()
        new_job.path_station_to_home = self.path_station_to_home.copy()
        return new_job

    def reset(self):
        """Reset job state to initial created state, remove paths."""
        self.path_robot_to_item = []
        self.path_item_to_station = []
        self.path_station_to_home = []
        self.state = JobState.WAITING_TO_START

    def start(self):
        """Transition WAITING_TO_START -> PICKING_ITEM"""
        if self.state != JobState.WAITING_TO_START:
            raise ValueError(f'Cannot start in current state {self.state}')
        self.state = JobState.PICKING_ITEM

    def pick_item(self):
        """Transition PICKING_ITEM -> ITEM_PICKED"""
        if self.state != JobState.PICKING_ITEM:
            raise ValueError(f'Cannot pick item in current state {self.state}')
        self.state = JobState.ITEM_PICKED

    def going_to_station(self):
        """Transition ITEM_PICKED -> GOING_TO_STATION"""
        if self.state != JobState.ITEM_PICKED:
            raise ValueError(
                f'Cannot go to station in current state {self.state}')
        self.state = JobState.GOING_TO_STATION

    def drop_item(self):
        """Transition GOING_TO_STATION -> ITEM_DROPPED"""
        if self.state != JobState.GOING_TO_STATION:
            raise ValueError(f'Cannot drop item in current state {self.state}')
        self.state = JobState.ITEM_DROPPED

    def return_home(self):
        """Transition ITEM_DROPPED -> RETURNING_HOME"""
        if self.state != JobState.ITEM_DROPPED:
            raise ValueError(
                f'Cannot return home in current state {self.state}')
        self.state = JobState.RETURNING_HOME

    def complete(self):
        """Transition RETURNING_HOME -> COMPLETE"""
        if self.state != JobState.RETURNING_HOME:
            raise ValueError(
                f'Cannot complete job in current state {self.state}')
        self.state = JobState.COMPLETE

    def error(self):
        """Transition to ERROR"""
        self.state = JobState.ERROR

    def __repr__(self):
        return (f'Job [Robot {self.robot_id}, Task {self.task_key}]: {self.state.name}, '
                f'P {len(self.path_robot_to_item)} {len(self.path_item_to_station)} '
                f'{len(self.path_station_to_home)}')
