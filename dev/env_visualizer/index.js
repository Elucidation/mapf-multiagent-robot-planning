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


let positions = [];
/**
 * Read X from DB and emit updated robot positions.
 */
async function update_latest_robot_positions() {
    dbm.open_db();
    let tasks = await dbm.get_tasks();
    positions = [];
    tasks.forEach(task => {
        // todo: Arbitrarily create robot position based on task id and item ids.
        positions.push({ x: task.item_id, y: task.id })
    });
    dbm.close_db();
    io.emit('update_robots', positions);
}

// Update robot positions every second.
let position_timer = setInterval(async () => {
    update_latest_robot_positions();
}, 1000);