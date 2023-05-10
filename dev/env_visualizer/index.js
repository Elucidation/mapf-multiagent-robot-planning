// @ts-check

// Can use the following env variables:
// PORT = port used by socket io
// REDIS_HOST & REDIS_PORT = url and port for redis server

// TODO: Serve a web page that shows a live view of the robots

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
  console.log(`New connection: ${socket.id} - ${socket.conn.remoteAddress}`);
  socket.emit("set_world", world);
  socket.emit("update", world);
  socket.conn.on("close", (reason) => {
    console.log(
      `Closed connection: ${socket.id} - ${socket.conn.remoteAddress} - ${reason}`
    );
  });
});

server.listen(port, () => {
  console.info(`SocketIO server listening on *:${port}`);
});

// Open databases
const { robot_dbm } = require("./database");
robot_dbm.open_db();

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
          pos: new Point(robot_home_zone.x, robot_home_zone.y),
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

// Set up Redis
const REDIS_HOST = process.env.REDIS_HOST || "localhost";
const REDIS_PORT = parseInt(process.env.REDIS_PORT || "6379");
const redis = require("redis");
/** @type{redis.RedisClientType} */
var r_client;

(async () => {
  console.log(`Trying to connect to redis server ${REDIS_HOST}:${REDIS_PORT}`);
  // Set up redis client (1 of 2)
  r_client = redis.createClient({
    socket: {
      host: REDIS_HOST,
      port: REDIS_PORT,
      reconnectStrategy() {
        console.debug("Waiting for redis server...");
        return 5000; // 5 seconds
      },
    },
  });
  r_client.on("error", (err) => {
    if (err.code != "ECONNREFUSED") console.warn("Redis error:", err.code);
  });
  await r_client.connect(); // Wait for connection

  console.log(await r_client.set("foo", "bar")); // 'OK'
  console.log(await r_client.get("foo")); // 'bar'

  // Set up subscriber redis client (2 of 2)
  const subscriber = redis.createClient({
    socket: {
      host: REDIS_HOST,
      port: REDIS_PORT,
      reconnectStrategy() {
        console.debug("Waiting for redis server...");
        return 5000; // 5 seconds
      },
    },
  });
  subscriber.on("error", (err) => {
    console.warn("Redis subscriber error:", err.code);
  });

  subscriber.on("ready", function () {
    console.log(`Redis subscriber READY ${REDIS_HOST}:${REDIS_PORT}`);
  });
  await subscriber.connect();

  // Set up callback on WORLD_T publish
  subscriber.subscribe("WORLD_T", (world_t_str) => {
    world.t = parseInt(world_t_str);
    update_robots();
    // TODO : Port this over to using redis
    // update_ims_table();
  });

  console.log(
    `Client subscriber connected to redis server ${REDIS_HOST}:${REDIS_PORT}`
  );

  update_ims_table();
})();

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

async function update_ims_table() {
  console.log("Call update_ims_table");

  // Get up to the oldest 10 new orders from the queue [0 - 9] = 10 entries
  const new_order_keys = await r_client.lRange("orders:new", 0, 9);

  // Get up to the latest 10 finished orders
  const finished_orders = await r_client.xRevRange(
    "orders:finished",
    "+",
    "-",
    { COUNT: 10 }
  );
  // finished_orders = list [
  //   {
  //     id: '1683752293575-0',
  //     message: [Object: null prototype] {
  //       order_id: '18',
  //       created: '1683752269.519895',
  //       items: '{"1": 1, "0": 2, "4": 1}',
  //       station: 'station:2'
  //     }
  //   }, ... ]

  // Get Stations (and any orders they contain)
  
  // Use a pipeline to get calls at once
  const r_multi = r_client.multi();
  r_multi.sMembers("stations:free");
  r_multi.sMembers("stations:busy");
  const [free_station_keys, busy_station_keys] = await r_multi.exec();

  console.log("new", new_order_keys);
  console.log("finished", finished_orders.length);
  console.log("free stations", free_station_keys);
  console.log("busy stations", busy_station_keys);

  console.log("todo");
  //   Promise.all(
  //     [dbm.get_new_orders(10),
  //     dbm.get_stations_and_order(),
  //     dbm.get_finished_orders(10),
  //     dbm.get_order_counts()]
  //   ).then(result => {
  //     const all_orders = {
  //       'new': result[0],
  //       'station': result[1],
  //       'finished': result[2],
  //       'counts': result[3]
  //     }

  //     io.emit("ims_all_orders", all_orders);
  //   })
}
