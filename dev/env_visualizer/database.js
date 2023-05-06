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
          console.error(err.message, this.db_path);
        } else {
          console.info("Connected to SQLITE DB", this.db_path);
        }
      }
    );
    this.cache = {
      newOrders: null,
      lastUpdateNew: null,
      finishedOrders: null,
      lastUpdateFinished: null,
      cacheDurationMs: 1000,
    };
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

  async get_new_orders(limit_rows) {
    // order_by column name; created or finished for example
    // direction is ASC default, DESC for reverse
    const currentTime = Date.now();

    // If cache is valid and not older than cacheDuration, return the cached data
    if (
      this.cache.newOrders !== null &&
      this.cache.lastUpdateNew !== null &&
      currentTime - this.cache.lastUpdateNew < this.cacheDurationMs
    ) {
      return this.cache.newOrders;
    }

    const query = `
    SELECT
    "Order".*,
    GROUP_CONCAT(OrderItem.item_id) AS item_ids,
	  GROUP_CONCAT(OrderItem.quantity) AS item_quantities
    FROM
        "Order"
    JOIN
        OrderItem ON "Order".order_id = OrderItem.order_id
    WHERE
        "Order".status = 'OPEN'
    GROUP BY
        "Order".order_id
    ORDER BY
        "Order".created
    LIMIT ?;`;

    return new Promise((resolve, reject) => {
      this.db.all(query, [limit_rows], (err, rows) => {
        if (err) {
          reject(err);
        } else {
          // split up item_ids/quantities into lists
          rows.forEach((row) => {
            row.item_ids = row.item_ids.split(",").map(Number);
            row.item_quantities = row.item_quantities.split(",").map(Number);
          });

          // Update cache and return
          this.cache.newOrders = rows;
          this.cache.lastUpdateNew = currentTime;
          resolve(rows);
        }
      });
    });
  }

  async get_finished_orders(limit_rows) {
    // finished_orders = dboi.get_orders(
    //   limit_rows=subset, direction="DESC", status="COMPLETE", order_by='finished')
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
          console.error(err.message, this.db_path);
        } else {
          console.info("Connected to SQLITE DB", this.db_path);
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

exports.dbm = new DatabaseManager(
  process.env.ORDERS_DB_PATH || "/data/orders.db"
);
exports.robot_dbm = new RobotDatabaseManager(
  process.env.WORLD_DB_PATH || "/data/world.db"
);
