// @ts-check

// TODO: Serve a web page that shows a live view of the robots
// TODO: Show orders too?
// TODO: Animate robot motion

const express = require('express');
const app = express();
const http = require('http');
const path = require('path');
const server = http.createServer(app);
const { Server } = require("socket.io");
const io = new Server(server);
const port = process.env.PORT || 3000;
const yaml = require('js-yaml');
const fs = require('fs');


app.use(express.static(path.join(__dirname, "www")));

app.get('/', (req, res) => {
    res.sendFile('/index.html');
});


io.on('connection', (socket) => {
    // Create arbitrary grid and initial robots.
    socket.emit('set_world', world);
    socket.emit('update', world);
});


server.listen(port, () => {
    console.info(`Listening on *:${port}`);
});

// Task Database (unneeded)
const { robot_dbm } = require('./database');
robot_dbm.open_db()
// robot_dbm.get_robots().then((x) => console.info(x))

// World

// TODO: use same function as visulizer.js 
class Point {
    constructor(/** @type {number} */ x, /** @type {number} */ y) {
        this.x = x;
        this.y = y;
    }

    equals(/** @type {Point} */ pt) {
        return this.x == pt.x && this.y == pt.y
    }
}

class Robot {
    constructor(data) {
        this.id = data.id;
        /** @type {Point} Current robot position*/
        this.pos = data.pos;
    }
}

class World {
    constructor(data) {
        // Warehouse data positions are using row, col units
        // For Points, we use x/y, x = col, y = row

        /** @type {number} The current time step (discrete, increments) */
        this.t = 0;
        /** @type {Robot[]} List of robots in this world */
        this.robots = [];
        for (let i = 0; i < data.robot_home_zones.length; i++) {
            const robot_home_zone = data.robot_home_zones[i];
            this.robots.push(new Robot({ id: i, pos: new Point(robot_home_zone[1], robot_home_zone[0])}))
        }
        /** @type {Point[]} Item loading positions in this world */
        this.item_load_positions = data.item_load_zones.map(rc => new Point(rc[1], rc[0]));
        /** @type {Point[]} Station positions in this world */
        this.station_positions = data.station_zones.map(rc => new Point(rc[1], rc[0]));
        /** @type {number[][]} Grid of world */
        this.grid = data.grid;
    }

    static from_yaml(/** @type {string} */ warehouse_path) {
        return new World(yaml.load(fs.readFileSync(warehouse_path, 'utf8')));
    }

    /**
     * 
     * @returns A dict with the static world info (grid, item and station positions)
     */
    get_world() {
        return {
            grid: this.grid,
            item_load_positions: this.item_load_positions,
            station_positions: this.station_positions
        };
    }
}


let world = World.from_yaml('../warehouses/warehouse1.yaml')


// Update robot positions every second
setInterval(update_robots, 1000); // 1 second
function update_robots() {
    Promise.all([robot_dbm.get_timestamp(), robot_dbm.get_robots()]).then(data => {
        let t_db_data = data[0];
        let robots_db_data = data[1];
        // Update time if exists
        if (t_db_data) {
            world.t = t_db_data.value;
        }
        
        // Update robot positions
        // Unparse "1,2" -> [1,2] for robot positions
        let robots = []
        for (let i = 0; i < robots_db_data.length; i++) {
            const robot = robots_db_data[i];
            let pos = robot.position.split(',').map(c => parseInt(c))
            world.robots[i].pos.x = pos[0]
            world.robots[i].pos.y = pos[1]
            robots.push({id:robot.robot_id, pos:{x:pos[0], y:pos[1]}, state:robot.state, held_item_id:robot.held_item_id})
        }

        let msg = {t:world.t, robots:robots}
        io.emit('update', msg);
    })
}