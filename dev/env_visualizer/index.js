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
    socket.on('disconnect', () => {
        io.emit('chat message', '-- a user disconnected');
    });
    socket.on('chat message', (msg) => {
        io.emit('chat message', msg);
    });
    io.emit('chat message', '-- a user connected');
});


server.listen(port, () => {
    console.log(`Listening on *:${port}`);
});

// Database
const database = require('./database');
console.log(database)

// const { readFile } = require('fs').promises;

// const app = express();
// app.get('/', async (request, response) => {
//     response.send(await readFile('./home.html', 'utf8'));
// });

