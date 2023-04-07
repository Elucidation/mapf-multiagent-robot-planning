// @ts-check

// TODO: Serve a web page that shows a live view of the robots
// TODO: Show orders too?
// TODO: Animate robot motion
// TODO: socket.io push state updates

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
    
    // TODO : Poll the DB containing robot positions and update from that instead
    // // When world_sim.py client emits update t/robots
    // socket.on('world_sim_robot_update', (data) => {
    //     // TODO (#16)
    //     console.info('Got world_sim_robot_update', data.t, data.timestamp);
    //     io.emit('update', data);
    //     return true;
    // })
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

    /**
     * 
     * @returns A dict with the current world state {t: time, positions: Point[] of robots}
     */
    get() {
        let data = { t: this.t }
        data.positions = this.robots.map((r) => r.pos);
        return data;
    }
}


let world = World.from_yaml('../warehouses/warehouse1.yaml')


// Update robot positions every second
setInterval(update_robots, 1000); // 1 second
function update_robots() {
    robot_dbm.get_robots().then((robots, idx) => {
        // console.info(x)
        let msg = {};
        msg.robots = [];
        robots.forEach(robot => {
            let pos = robot.position.split(',').map(c => parseInt(c))
            msg.robots.push({id:robot.robot_id, pos:{x:pos[0], y:pos[1]}, state:robot.state, held_item_id:robot.held_item_id})
        });
        // msg is {robots: [{id, pos},...], t:timestamp}, pos is list of x/y positions [{x:..., y:...}, ...] for each robot}
        io.emit('update', msg);
    })
}