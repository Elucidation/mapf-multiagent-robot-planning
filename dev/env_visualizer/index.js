// @ts-check 

// TODO: Serve a web page that shows a live view of the robots
// TODO: Show orders too?
// TODO: Animate robot motion
// TODO: socket.io push state updates

// const express = require('express');
const express = require('express');
const app = express();
const http = require('http');
const path = require('path');
const server = http.createServer(app);
const { Server } = require("socket.io");
const io = new Server(server);
const port = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, "www")));

app.get('/', (req, res) => {
    res.sendFile('/index.html');
});


io.on('connection', (socket) => {
    // Create arbitrary grid and initial robots.
    socket.emit('set_world', world);
    socket.emit('update', world);
    
    // When world_sim.py client emits static update t/robots/grid/etc.
    socket.on('world_sim_static_update', (data) => {
        // TODO (#16)
        console.info('Got world_sim_static_update', data.t, data.timestamp);
        world = data;
        io.emit('set_world', data);
        io.emit('update', data);
        return true;
    })

    // When world_sim.py client emits update t/robots
    socket.on('world_sim_robot_update', (data) => {
        // TODO (#16)
        console.info('Got world_sim_robot_update', data.t, data.timestamp);
        io.emit('update', data);
        return true;
    })
});


server.listen(port, () => {
    console.info(`Listening on *:${port}`);
});

// Database
const { dbm } = require('./database');
console.info(dbm)

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
        /** @type {Point[]} Current path for robot */
        this.path = [];
    }

    step() {
        // Update position to next point on the path if it exists, 
        // stay in the same position otherwise.
        let next_pos = this.path.shift();
        if (next_pos) {
            this.pos = next_pos;
        }
    }

    add_path(/** @type {Point[]} */ path) {
        let next_pos = this.pos;
        if (this.path.length > 0) {
            next_pos = this.path[-1];
        }
        if (!path[0].equals(next_pos)) {
            console.error('Tried to add path not beginning at current final robot position:', next_pos, path);
            return;
        }
        this.path = this.path.concat(path);
        console.debug('Added path', path)
    }
}

class World {
    constructor(data) {
        /** @type {number} The current time step (discrete, increments) */
        this.t = data.t;
        /** @type {Robot[]} List of robots in this world */
        this.robots = data.robots;
        /** @type {Point[]} Item loading positions in this world */
        this.item_load_positions = data.item_load_positions;
        /** @type {Point[]} Station positions in this world */
        this.station_positions = data.station_positions;
        /** @type {number[][]} Grid of world */
        this.grid = data.grid;
    }

    step() {
        this.robots.forEach(robot => {
            robot.step();
        });
        this.t += 1;
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

let r1 = new Robot({ id: 1, pos: new Point(1, 2) });
let r2 = new Robot({ id: 2, pos: new Point(3, 5) });
let r3 = new Robot({ id: 3, pos: new Point(2, 3) });

let grid = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]

let item_load_positions = [
    new Point(2, 3),
    new Point(2, 5),
    new Point(2, 7)
];
let station_positions = [
    new Point(8, 2),
    new Point(8, 5),
    new Point(8, 8)
];
let world = new World({
    grid: grid,
    item_load_positions: item_load_positions,
    station_positions: station_positions,
    t: 0,
    robots: [r1, r2, r3]
});