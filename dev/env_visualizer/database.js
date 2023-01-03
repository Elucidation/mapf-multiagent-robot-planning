const sqlite3 = require('sqlite3').verbose();
/**
 * Provides accessors to Order/Station/Task Database
 */
class DatabaseManager {
    constructor(path) {
        this.db_path = path;
    }

    open_db() {
        this.db = new sqlite3.Database(this.db_path, sqlite3.OPEN_READONLY, (err) => {
            if (err) {
                console.error(err.message);
            }
            // console.debug('Connected to the database.');
        });
    }

    close_db() {
        this.db.close((err) => {
            if (err) {
                console.error(err.message);
            }
            // console.debug('Closed the database connection.');
        })
    }

    async get_tasks() {
        return new Promise((resolve, reject) => {
            this.db.all("SELECT rowid as id, * FROM Task", (err, rows) => {
                if (err)
                    return reject(err);
                resolve(rows);
            });
        });
    }
}

exports.dbm = new DatabaseManager('../inventory_management_system/orders.db');