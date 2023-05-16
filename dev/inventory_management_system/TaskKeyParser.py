"""Helper functions to parse a task_key or task_group_key into components
Task key contains 'task:station:<id>:order:<id>:<item_id>:<idx>'
"""
from collections import namedtuple

from .Item import ItemId
from .Order import OrderId
from .Station import StationId

TaskIds = namedtuple('TaskIds', ['station_id', 'order_id', 'item_id', 'idx'])
TaskSubKeys = namedtuple(
    'TaskSubKeys', ['task_group_key', 'station_key', 'order_key', 'item_id', 'idx'])


# Task key: 'task:station:<id>:order:<id>:<item_id>:<idx>'
def parse_task_key_to_ids(task_key) -> TaskIds:
    """Returns TaskIds(station_id, order_id, item_id, idx)"""
    _, _, station_id, _, order_id, item_id, idx = task_key.split(':')
    return TaskIds(
        StationId(int(station_id)), OrderId(int(order_id)), ItemId(int(item_id)), int(idx))


def parse_task_key_to_keys(task_key) -> TaskSubKeys:
    """Returns TaskSubKeys(task_group_key, station_key, order_key, item_id, idx)"""
    _, _, station_id, _, order_id, item_id, idx = task_key.split(':')
    return TaskSubKeys(f'station:{station_id}:order:{order_id}', f'station:{station_id}',
                       f'order:{order_id}', ItemId(int(item_id)), int(idx))


def parse_task_key_to_group(task_key: str):
    """Return (task_group_key, item_id, idx)"""
    # Task key contains it all 'task:station:<id>:order:<id>:<item_id>:<idx>'
    task_group_key, item_id, idx = task_key.rsplit(':', 2)
    return (task_group_key, ItemId(int(item_id)), int(idx))


# Task group key: 'task:station:<id>:order:<id>'
def parse_task_group_key_to_ids(task_group_key: str):
    """Return (station_id, order_id)"""
    # Task key contains it all 'task:station:<id>:order:<id>'
    _, _, station_id, _, order_id = task_group_key.split(':')
    return (StationId(int(station_id)), OrderId(int(order_id)))


def parse_task_group_key(task_group_key: str):
    """Return (station_key, order_key)"""
    # Task key contains it all 'task:station:<id>:order:<id>'
    _, _, station_id, _, order_id = task_group_key.split(':')
    return (f'station:{station_id}', f'order:{order_id}')
