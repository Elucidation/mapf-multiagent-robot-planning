const sqlite3 = require("sqlite3").verbose();

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

exports.robot_dbm = new RobotDatabaseManager(
  process.env.WORLD_DB_PATH || "/data/world.db"
);
