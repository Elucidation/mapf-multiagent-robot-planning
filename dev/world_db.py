# DB interface class for world simulator to store world state in a SQL DB
# Using sqlite instead of tinydb for a bit more concurrent read stability

import sqlite3 as sl
from typing import List
import logging
from robot import Robot, RobotId

MAIN_DB = "orders.db"

# Set up logging
logger = logging.getLogger("database_world_manager")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)


class WorldDatabaseManager:
    """DB Manager for world state"""

    def __init__(self, db_filename):
        self.con = sl.connect(db_filename)
        # TODO: need to reset if new db
        
    def reset(self):
        self.delete_tables()
        self.init_tables()

    def delete_tables(self):
        self.con.executescript(
            """
            DROP TABLE IF EXISTS "Robot";
            """)

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
                "path"   TEXT DEFAULT "",
                PRIMARY KEY("robot_id")
            );
            """)
    
    def add_robots(self, robots: List[Robot]):
        data = []
        # Array of tuples (id, "x,y") for each robot
        for robot in robots:
            pos_str = f'{robot.pos[0]},{robot.pos[1]}'
            data.append([robot.id, pos_str])
        
        cursor = self.con.cursor()
        print('add_robots', data)
        sql = """INSERT INTO Robot (robot_id, position) VALUES (?, ?) """
        cursor.executemany(sql, data)
        self.con.commit()
    
    def update_robot_states(self, robots: List[Robot]):
        data = []
        # Array of tuples ("x,y", robot_id) for each robot
        for robot in robots:
            pos_str = f'{robot.pos[0]},{robot.pos[1]}'
            data.append([pos_str, robot.id])
        
        cursor = self.con.cursor()
        sql = """UPDATE Robot SET position=? WHERE robot_id=?"""
        cursor.executemany(sql, data)
        self.con.commit()


if __name__ == '__main__':
    wdm = WorldDatabaseManager('world.db')
    wdm.reset()
    wdm.add_robots([Robot(RobotId(0),(1,2)), Robot(RobotId(1),(3,5))])
    