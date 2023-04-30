// @ts-check

// TODO: Serve a web page that shows a live view of the robots
// TODO: Show orders too?
// TODO: Animate robot motion

const express = require("express");
const app = express();
const http = require("http");
const path = require("path");
const server = http.createServer(app);
const { Server } = require("socket.io");
const io = new Server(server);
const port = process.env.PORT || 3000;
const yaml = require("js-yaml");
const fs = require("fs");

app.use(express.static(path.join(__dirname, "www")));

app.get("/", (req, res) => {
  res.sendFile("/index.html");
});

io.on("connection", (socket) => {
  // Create arbitrary grid and initial robots.
  console.log(`New connection: ${socket.id} - ${socket.conn.remoteAddress}`)
  socket.emit("set_world", world);
  socket.emit("update", world);
  socket.conn.on("close", (reason) => {
    console.log(`Closed connection: ${socket.id} - ${socket.conn.remoteAddress} - ${reason}`)
  });
});

server.listen(port, () => {
  console.info(`Listening on *:${port}`);
});

// Open databases
const { robot_dbm, dbm } = require("./database");
robot_dbm.open_db();
dbm.open_db();

// World

// TODO: use same function as visulizer.js
class Point {
  constructor(/** @type {number} */ x, /** @type {number} */ y) {
    this.x = x;
    this.y = y;
  }

  equals(/** @type {Point} */ pt) {
    return this.x == pt.x && this.y == pt.y;
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

    /** @type {number} The time step delta in seconds */
    this.dt_s = NaN;

    /** @type {Point[]} Robot Home positions in this world */
    this.robot_home_zones = data.robot_home_zones.map(
      (rc) => new Point(rc[1], rc[0])
    );

    /** @type {Point[]} Item loading positions in this world */
    this.item_load_positions = data.item_load_zones.map(
      (rc) => new Point(rc[1], rc[0])
    );

    /** @type {Point[]} Station positions in this world */
    this.station_positions = data.station_zones.map(
      (rc) => new Point(rc[1], rc[0])
    );

    /** @type {Robot[]} List of robots in this world */
    this.robots = [];
    for (let i = 0; i < this.robot_home_zones.length; i++) {
      const robot_home_zone = this.robot_home_zones[i];
      this.robots.push(
        new Robot({
          id: i,
          pos: new Point(robot_home_zone[1], robot_home_zone[0]),
        })
      );
    }

    /** @type {number[][]} Grid of world */
    this.grid = data.grid;

    /** @type {string[]} Names of items with zero-indexed ids  */
    this.item_names = World.load_item_names();
  }

  static load_item_names() {
    return fs
      .readFileSync("./inventory_management_system/item_names.txt")
      .toString()
      .replace(/\r\n/g, "\n")
      .split("\n");
  }

  static from_yaml(/** @type {string} */ warehouse_path) {
    return new World(yaml.load(fs.readFileSync(warehouse_path, "utf8")));
  }

  /**
   *
   * @returns A dict with the static world info
   */
  get_world() {
    return {
      grid: this.grid,
      item_load_positions: this.item_load_positions,
      station_positions: this.station_positions,
      robot_home_zones: this.robot_home_zones,
      item_names: this.item_names,
    };
  }
}

var world = World.from_yaml("./warehouses/warehouse3.yaml");

// Let visualizer know expected update rate
robot_dbm.get_dt_sec().then((data) => {
  world.dt_s = data.value;
});

// 0MQ Subscribe for world step updates
const zmq = require("zeromq");
const { stringify } = require("querystring");
const ZMQ_PORT = process.env.ZMQ_PORT || "50523";
const ZMQ_HOST = process.env.ZMQ_HOST || "localhost";


async function run() {
  const sock = new zmq.Subscriber();

  sock.connect(`tcp://${ZMQ_HOST}:${ZMQ_PORT}`);
  sock.subscribe("WORLD");
  console.log(`Subscriber connected to ${ZMQ_HOST}:${ZMQ_PORT}`);

  // Parse world time step from the 0MQ published message ex: 'WORLD N'
  for await (const [full_msg] of sock) {
    let parts = String(full_msg).split(" ");
    if (parts.length != 2 && parts[0] != "WORLD") {
      continue;
    }
    world.t = parseInt(parts[1]);
    update_robots();
  }
}

run();

function update_ims() {
  // TODO : Use this to show station states
  // Update IMS stations/orders/items viz
  processStationsAndOrderItems();
}

async function processStationsAndOrderItems() {
  try {
    const stations = await dbm.get_stations();
    const order_ids = stations.map((station) => station.order_id);
    const order_items = await dbm.get_order_items_by_ids(order_ids);
    // do_something();
  } catch (error) {
    console.error("Error processing stations and order items:", error);
  }
}

function update_robots() {
  robot_dbm.get_robots().then((robots_db_data) => {
    // Update robot positions
    let robots = [];
    for (let i = 0; i < robots_db_data.length; i++) {
      const robot = robots_db_data[i];
      let pos = JSON.parse(robot.position);
      let path = JSON.parse(robot.path);

      world.robots[i].pos.x = pos[0];
      world.robots[i].pos.y = pos[1];
      robots.push({
        id: robot.robot_id,
        pos: { x: pos[0], y: pos[1] },
        state: robot.state,
        held_item_id: robot.held_item_id,
        path: path, // future path [(x,y), (x,y), ...], empty [] otherwise
      });
    }

    let msg = { t: world.t, robots: robots, dt_s: world.dt_s };
    io.emit("update", msg);
  });
}
