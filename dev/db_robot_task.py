# Helper script to create or clear the Robot Task Allocation DB
import sqlite3 as sl



# Todo : convert to class

if __name__ == "__main__":
    DB_NAME = "robot_task_allocations.db"
    con = sl.connect(DB_NAME)
    with con:
        con.executescript("""
        DROP TABLE IF EXISTS "Order";
        DROP TABLE IF EXISTS "Item";
        DROP TABLE IF EXISTS "OrderItem";
        DROP TABLE IF EXISTS "Station";
        DROP TABLE IF EXISTS "Task";

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
