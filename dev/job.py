"""Job class for tracking Robot-Task allocations"""

from typing import NewType
from inventory_management_system.Order import OrderId
from inventory_management_system.Station import StationId
from inventory_management_system.Item import ItemId
from multiagent_planner.pathfinding import Position, Path
from robot import RobotId

JobId = NewType('JobId', int)

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
        self.path_robot_to_item: Path
        self.path_item_to_station: Path
        self.path_station_to_home: Path

        self.reset()

    def reset(self):
        # Paths
        self.path_robot_to_item = []
        self.path_item_to_station = []
        self.path_station_to_home = []

        # State tracker, ladder logic
        # TODO : Replace this with state object
        self.started = False
        self.item_picked = False
        self.going_to_station = False
        self.item_dropped = False
        self.returning_home = False
        self.robot_returned = False
        self.complete = False
        self.error = False
    
    def __repr__(self):
        state = [self.started, self.item_picked, self.going_to_station,
                 self.item_dropped, self.returning_home,
                 self.robot_returned, self.complete, self.error]
        state_str = ""
        if self.error:
            state_str = "ERROR"
        elif self.complete:
            state_str = "COMPLETE"
        elif self.robot_returned:
            state_str = "RETURNED"
        elif self.returning_home:
            state_str = "GOING HOME"
        elif self.item_dropped:
            state_str = "ITEM DROPPED"
        elif self.going_to_station:
            state_str = "GOING TO STATION"
        elif self.item_picked:
            state_str = "ITEM PICKED"
        elif self.started:
            state_str = "STARTED"
        else:
            state_str = "OPEN"

        state = [int(s) for s in state]
        return (f'Job [Robot {self.robot_id}, Task {self.task_key}: Progress {state_str}, '
                f'P {len(self.path_robot_to_item)} {len(self.path_item_to_station)} '
                f'{len(self.path_station_to_home)}')