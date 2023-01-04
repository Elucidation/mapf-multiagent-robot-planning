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
    io.emit('set_grid', { x: 30, y: 10 });
    io.emit('update_robots', [{ x: 1, y: 2 }, { x: 3, y: 2 }])
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
    }

    step() {
        this.robots.forEach(robot => {
            robot.step();
        });
        this.t += 1;
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
let world = new World({ t: 0, robots: [r1, r2, r3] });

r2.add_path([
    new Point(3, 5),
    new Point(4, 5),
    new Point(5, 5)
])

console.log(world);
// let positions = [];
/**
 * Read X from DB and emit updated robot positions.
 */
// async function update_latest_robot_positions() {
//     dbm.open_db();
//     let tasks = await dbm.get_tasks();
//     positions = [];
//     tasks.forEach(task => {
//         // todo: Arbitrarily create robot position based on task id and item ids.
//         positions.push({ x: task.item_id, y: task.id })
//     });
//     dbm.close_db();
//     io.emit('update_robots', positions);
// }

// Update robot positions every second.
let position_timer = setInterval(async () => {
    // update_latest_robot_positions();
    world.step();
    let data = world.get();
    io.emit('update', data);
}, 1000);

setTimeout(() => {
    r2.add_path([
        new Point(5, 5),
        new Point(5, 6),
        new Point(5, 7),
        new Point(5, 8),
    ])
}, 5000);