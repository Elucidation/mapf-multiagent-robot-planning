# Helper script to create or clear the Robot Task Allocation DB
import logging
import sqlite3 as sl

class DatabaseRobotTaskManager:
    """Manager for interacting with the Robot/Task Allocation database"""
    DB_NAME = "robot_task_allocations.db"

    def __init__(self, db_filename=DB_NAME):
        self.db_filename = db_filename
        self.con = sl.connect(db_filename)
        self.init_logging()
        # TODO: need to reset if new db
        self.reset()

    def init_logging(self):
        # Set up logging
        self.logger = logging.getLogger("database_order_manager")
        self.logger.setLevel(logging.DEBUG)
        log_handler = logging.StreamHandler()
        log_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(log_handler)

    def reset(self):
        self.delete_tables()
        self.init_tables()

    def delete_tables(self):
        self.con.executescript(
            """DROP TABLE IF EXISTS "RobotTaskAllocation";""")

    def init_tables(self):
        self.con.executescript("""
            CREATE TABLE "RobotTaskAllocation" (
            "allocation_id" INTEGER NOT NULL,
            "robot_id"  INTEGER NOT NULL,
            "task_id" INTEGER NOT NULL,
            "item_picked" INTEGER NOT NULL DEFAULT 0,
            "item_dropped"  INTEGER NOT NULL DEFAULT 0,
            "robot_returned"  INTEGER NOT NULL DEFAULT 0,
            "complete"  INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY("allocation_id" AUTOINCREMENT)
            );
            """)

if __name__ == "__main__":
    db_rtm = DatabaseRobotTaskManager()
