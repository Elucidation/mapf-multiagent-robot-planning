""" Helper function to load a warehouse yaml file."""
from typing import List, Tuple
import numpy as np
import yaml

Position = Tuple[int, int]


def flip_rc_xy(path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    return [(c, r) for (r, c) in path]


def load_warehouse_yaml(filename: str) -> Tuple[
        np.ndarray, List[Position], List[Position], List[Position]]:
    """Load a warehouse yaml containing world grid and positions of stations/robots etc."""
    with open(filename, 'r', encoding='utf8') as file:
        scenario = yaml.safe_load(file)
    grid = np.array(scenario['grid'])
    robot_home_zones = [(int(r), int(c))
                        for (r, c) in scenario['robot_home_zones']]
    item_load_zones = [(int(r), int(c))
                       for (r, c) in scenario['item_load_zones']]
    station_zones = [(int(r), int(c)) for (r, c) in scenario['station_zones']]
    return grid, robot_home_zones, item_load_zones, station_zones


def load_warehouse_yaml_xy(filename: str) -> Tuple[
        np.ndarray, List[Position], List[Position], List[Position]]:
    """ Load warehouse yaml in x,y coordinates instead of row, col (flipped)"""
    grid, robot_home_zones, item_load_zones, station_zones = load_warehouse_yaml(
        filename)
    robot_home_zones = flip_rc_xy(robot_home_zones)
    item_load_zones = flip_rc_xy(item_load_zones)
    station_zones = flip_rc_xy(station_zones)

    return grid.transpose(), robot_home_zones, item_load_zones, station_zones
