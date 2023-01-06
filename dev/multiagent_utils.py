import numpy as np
import yaml
from typing import List, Tuple

# TODO: Move scenarios to Scenario class
def get_scenario(filename: str) -> Tuple[np.ndarray, List[Tuple[int, int]], List[Tuple[int, int]]]:
    with open(filename, 'r') as f:
        scenario = yaml.safe_load(f)
    grid = np.array(scenario['grid'])
    goals = [(int(r), int(c)) for (r,c) in scenario['goals']]
    starts = [(int(r), int(c)) for (r,c) in scenario['starts']]
    return grid, goals, starts


if __name__ == '__main__':
    get_scenario('scenarios/scenario1.yaml')
