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
      stationOrders: null,
      lastUpdateStation: null,
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

  async get_stations_and_order() {
    // Returns station_id, and any/all order info associated
    const currentTime = Date.now();
    // If cache is valid and not older than cacheDuration, return the cached data
    if (
      this.cache.stationOrders !== null &&
      this.cache.lastUpdateStation !== null &&
      currentTime - this.cache.lastUpdateStation < this.cacheDurationMs
    ) {
      return this.cache.stationOrders;
    }

    // Stil
    const query = `
    SELECT
        Station.*,
        GROUP_CONCAT(CASE WHEN Task.status = 'COMPLETE' THEN Task.item_id ELSE NULL END) AS completed_item_ids,
        GROUP_CONCAT(CASE WHEN Task.status = 'COMPLETE' THEN OrderItem.quantity ELSE NULL END) AS completed_item_quantities,
        GROUP_CONCAT(CASE WHEN Task.status = 'OPEN' OR Task.status = 'IN_PROGRESS' THEN Task.item_id ELSE NULL END) AS open_item_ids,
        GROUP_CONCAT(CASE WHEN Task.status = 'OPEN' OR Task.status = 'IN_PROGRESS' THEN Task.quantity ELSE NULL END) AS open_item_quantities
    FROM
        Station
    LEFT JOIN
        "Order" ON Station.order_id = "Order".order_id
    LEFT JOIN
        Task ON "Order".order_id = Task.order_id
    LEFT JOIN
        OrderItem ON Task.item_id = OrderItem.item_id AND "Order".order_id = OrderItem.order_id
    GROUP BY
        Station.station_id
    ORDER BY
        Station.station_id
    ;`;

    return new Promise((resolve, reject) => {
      this.db.all(query, [], (err, rows) => {
        if (err) {
          reject(err);
        } else {
          // split up item_ids/quantities into lists
          rows.forEach((row) => {
            if (row.completed_item_ids) {
              row.completed_item_ids = row.completed_item_ids
                .split(",")
                .map(Number);
            }
            if (row.completed_item_quantities) {
              row.completed_item_quantities = row.completed_item_quantities
                .split(",")
                .map(Number);
            }
            if (row.open_item_ids) {
              row.open_item_ids = row.open_item_ids.split(",").map(Number);
            }
            if (row.open_item_quantities) {
              row.open_item_quantities = row.open_item_quantities
                .split(",")
                .map(Number);
            }
          });

          // Update cache and return
          this.cache.stationOrders = rows;
          this.cache.lastUpdateStation = currentTime;
          resolve(rows);
        }
      });
    });
  }

  async get_new_orders(limit_rows) {
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
    const currentTime = Date.now();
    // If cache is valid and not older than cacheDuration, return the cached data
    if (
      this.cache.finishedOrders !== null &&
      this.cache.lastUpdateFinished !== null &&
      currentTime - this.cache.lastUpdateFinished < this.cacheDurationMs
    ) {
      return this.cache.finishedOrders;
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
        "Order".status = 'COMPLETE'
    GROUP BY
        "Order".order_id
    ORDER BY
        "Order".finished
    DESC LIMIT ?;`;

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
          this.cache.finishedOrders = rows;
          this.cache.lastUpdateFinished = currentTime;
          resolve(rows);
        }
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
