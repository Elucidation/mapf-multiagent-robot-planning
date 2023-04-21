const sqlite3 = require("sqlite3").verbose();
/**
 * Provides accessors to Order/Station/Task Database
 */
class DatabaseManager {
  constructor(path) {
    this.db_path = path;
  }

  open_db() {
    this.db = new sqlite3.Database(
      this.db_path,
      sqlite3.OPEN_READONLY,
      (err) => {
        if (err) {
          console.error(err.message);
        }
      }
    );
  }

  close_db() {
    this.db.close((err) => {
      if (err) {
        console.error(err.message);
      }
    });
  }

  async get_stations() {
    // Returns station_id, optional order_id
    return new Promise((resolve, reject) => {
      this.db.all("SELECT * FROM Station", (err, rows) => {
        if (err) return reject(err);
        resolve(rows);
      });
    });
  }

  async get_order_items_by_ids(order_ids) {
    return new Promise((resolve, reject) => {
      if (!order_ids || !Array.isArray(order_ids) || order_ids.length === 0) {
        return reject(
          new Error("Invalid order IDs input. Must be a non-empty array.")
        );
      }
      const placeholders = order_ids.map(() => "?").join(",");
      const query = `SELECT order_id, item_id, quantity FROM "OrderItem" WHERE order_id IN (${placeholders})`;
      this.db.all(query, order_ids, (err, rows) => {
        if (err) {
          return reject(err);
        }
        resolve(rows);
      });
    });
  }

  async get_tasks() {
    return new Promise((resolve, reject) => {
      this.db.all("SELECT rowid as id, * FROM Task", (err, rows) => {
        if (err) return reject(err);
        resolve(rows);
      });
    });
  }
}

/**
 * Provides accessors to Robot Position Database
 */
class RobotDatabaseManager {
  constructor(path) {
    this.db_path = path;
  }

  open_db() {
    this.db = new sqlite3.Database(
      this.db_path,
      sqlite3.OPEN_READONLY,
      (err) => {
        if (err) {
          console.error(err.message);
        }
      }
    );
  }

  close_db() {
    this.db.close((err) => {
      if (err) {
        console.error(err.message);
      }
    });
  }

  async get_timestamp() {
    return new Promise((resolve, reject) => {
      this.db.get(
        "SELECT value FROM State WHERE label='timestamp'",
        (err, row) => {
          if (err) return reject(err);
          resolve(row);
        }
      );
    });
  }

  async get_dt_sec() {
    return new Promise((resolve, reject) => {
      this.db.get(
        "SELECT value FROM State WHERE label='dt_sec'",
        (err, row) => {
          if (err) return reject(err);
          resolve(row);
        }
      );
    });
  }

  async get_robots() {
    return new Promise((resolve, reject) => {
      this.db.all("SELECT * FROM Robot", (err, rows) => {
        if (err) return reject(err);
        resolve(rows);
      });
    });
  }
}

exports.dbm = new DatabaseManager("./inventory_management_system/orders.db");
exports.robot_dbm = new RobotDatabaseManager("./world.db");
