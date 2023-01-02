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
            console.log('Connected to the database.');
        });
    }

    close_db() {
        this.db.close((err) => {
            if (err) {
                console.error(err.message);
            }
            console.log('Closed the database connection.');
        })
    }

    get_tasks() {
        this.db.serialize(() => {
            this.db.each("SELECT rowid as id, * FROM Task", (err, row) => {
                console.log(`Task ${row.id} for Order ${row.order_id} Move item ${row.item_id} x${row.quantity} to Station ${row.station_id} [Status: ${row.status}]`);
            });
        });
    }
}

exports.dbm = new DatabaseManager('../inventory_management_system/orders.db');