"""
DB interface class for world simulator to store world state in a SQL DB
Using sqlite instead of tinydb for a bit more concurrent read stability
"""
import sqlite3 as sl
from typing import List, Optional
import functools
import logging
import json
import time
from robot import Robot, RobotId, RobotStatus, Position

WORLD_DB_PATH = 'world.db'

# Set up logging
logger = logging.getLogger("database_world_manager")

# Decorator for timing functions in WDB
def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f'{func.__name__!r} Start')
        t_start = time.perf_counter()
        result = func(*args, **kwargs)
        t_end = time.perf_counter()
        logger.debug(f'{func.__name__!r} End. Took {t_end - t_start:.6f} sec')
        return result
    return wrapper


class WorldDatabaseManager:
    """DB Manager for world state"""

    @timeit
    def __init__(self, db_filename):
        self.con = sl.connect(db_filename)
        logger.debug('Initialized WorldDatabaseManager instance')
        # Note: need to reset if new db

    @timeit
    def reset(self):
        self.delete_tables()
        self.init_tables()

    @timeit
    def delete_tables(self):
        self.con.executescript(
            """
            DROP TABLE IF EXISTS "Robot";
            DROP TABLE IF EXISTS "State";
            """)

    @timeit
    def init_tables(self):
        # path = text of list of grid positions (and timestamps?)
        # position = text of current x y grid position
        # last_trajectory_id = int of last trajectory given,
        #   if state available means that trajectory_id is finished?
        # state = text AVAILABLE / IN_PROGRESS (when available )
        # held_item_id = int item_id if it is holding something
        self.con.executescript(
            """
            CREATE TABLE IF NOT EXISTS "Robot" (
                "robot_id"  INTEGER NOT NULL UNIQUE,
                "position"   TEXT,
                "held_item_id" INTEGER,
                "state" TEXT DEFAULT "AVAILABLE",
                "path"   TEXT DEFAULT "[]",
                PRIMARY KEY("robot_id")
            );
            CREATE TABLE IF NOT EXISTS "State" (
                "label" TEXT UNIQUE,
                "value" INTEGER,
                "string_value" TEXT,
                PRIMARY KEY("label")
            );
            """)

    @timeit
    def add_robots(self, robots: List[Robot]):
        data = []
        # Array of tuples (id, "x,y") for each robot
        for robot in robots:
            pos_str = json.dumps(robot.pos)
            data.append([robot.robot_id, pos_str])

        cursor = self.con.cursor()
        print('add_robots', data)
        sql = """INSERT INTO Robot (robot_id, position) VALUES (?, ?) """
        cursor.executemany(sql, data)
        self.con.commit()

    @timeit
    def update_timestamp(self, t: int):
        cursor = self.con.cursor()
        sql = """REPLACE INTO State (label, value) VALUES ('timestamp', ?)"""
        cursor.execute(sql, (t,))
        self.con.commit()

    @timeit
    def set_dt_sec(self, dt_sec: float):
        cursor = self.con.cursor()
        sql = """REPLACE INTO State (label, value) VALUES ('dt_sec', ?)"""
        cursor.execute(sql, (dt_sec,))
        self.con.commit()

    @timeit
    def get_dt_sec(self) -> float:
        result = self.con.execute(
            'SELECT value FROM State WHERE label = "dt_sec" LIMIT 1')
        (dt_sec,) = result.fetchone()
        return dt_sec

    @timeit
    def set_robot_path(self, robot_id: int, path: list):
        # Note, tuples become lists with json.
        path_str = json.dumps(path)
        data = [path_str, robot_id]

        cursor = self.con.cursor()
        sql = """UPDATE Robot SET path=? WHERE robot_id=?"""
        cursor.execute(sql, data)
        self.con.commit()

    @timeit
    def update_robots(self, robots: List[Robot]):
        data = []
        # Array of tuples ("[x,y]", robot_id) for each robot
        for robot in robots:
            pos_str = json.dumps(robot.pos)
            path = json.dumps(list(robot.future_path))
            data.append([pos_str, robot.held_item_id,
                        str(robot.state), path, robot.robot_id])

        cursor = self.con.cursor()
        sql = """UPDATE Robot SET position=?, held_item_id=?, state=?, path=? WHERE robot_id=?"""
        cursor.executemany(sql, data)
        self.con.commit()

    def _parse_position(self, position_str: str) -> Position:
        pos_x, pos_y = json.loads(position_str)
        return (pos_x, pos_y)  # (x, y) for Robot

    def _parse_path(self, path_str: str) -> List[Position]:
        # Note: invalid path str will fail out on loads.
        path = json.loads(path_str)
        return [(x, y) for x, y in path]  # Create position tuples

    @timeit
    def get_robot(self, robot_id: RobotId) -> Robot:
        cursor = self.con.cursor()
        sql = ("SELECT robot_id, position, held_item_id, state, path FROM Robot "
               "WHERE robot_id = ? LIMIT 1")
        cursor.execute(sql, (robot_id,))
        (_, position_str, held_item_id, state_str, path_str) = cursor.fetchone()
        path = self._parse_path(path_str)
        position = self._parse_position(position_str)
        state = RobotStatus.load(state_str)
        return Robot(robot_id, position, held_item_id, state, path)

    @timeit
    def get_robots(self, query_state: Optional[str] = None) -> List[Robot]:
        cursor = self.con.cursor()
        if query_state:
            sql = "SELECT robot_id, position, held_item_id, state, path FROM Robot WHERE state = ?"
            cursor.execute(sql, (query_state,))
        else:
            sql = "SELECT robot_id, position, held_item_id, state, path FROM Robot"
            cursor.execute(sql)
        robots = []
        for row in cursor.fetchall():
            (robot_id, position_str, held_item_id, state_str, path_str) = row
            path = self._parse_path(path_str)
            state = RobotStatus.load(state_str)
            position = self._parse_position(position_str)
            robot = Robot(robot_id, position, held_item_id,
                          state, path)
            robots.append(robot)
        return robots


if __name__ == '__main__':
    wdm = WorldDatabaseManager(WORLD_DB_PATH)
    wdm.reset()
    wdm.add_robots([Robot(RobotId(0), (1, 2)), Robot(RobotId(1), (3, 5))])
    wdm.update_timestamp(3)
