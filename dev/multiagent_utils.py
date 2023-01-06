import numpy as np
import yaml

# TODO: Move scenarios to Scenario class
def get_scenario(filename):
    with open(filename, 'r') as f:
        scenario = yaml.safe_load(f)
    grid = np.array(scenario['grid'])
    goals = [tuple(x) for x in scenario['goals']]
    starts = [tuple(x) for x in scenario['starts']]
    return grid, goals, starts

if __name__ == '__main__':
    get_scenario('scenarios/scenario1.yaml')
