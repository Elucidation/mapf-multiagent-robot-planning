// @ts-check

// Can use the following env variables:
// PORT = port used by socket io
// REDIS_HOST & REDIS_PORT = url and port for redis server

// TODO: Serve a web page that shows a live view of the robots
console.log('Starting up, loading requires...');
const express = require("express");
const http = require("http");
const path = require("path");
const yaml = require("js-yaml");
const fs = require("fs");
const redis = require("redis");
console.log('Finished loading requires...');

const app = express();
const server = http.createServer(app);
const { Server } = require("socket.io");
const io = new Server(server);
const port = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, "www")));

// @ts-ignore
app.get("/", (req, res) => {
  res.sendFile("/index.html");
});

io.on("connection", (socket) => {
  // Create arbitrary grid and initial robots.
  console.log(
    `New connection: ${socket.id} - ${socket.conn.remoteAddress}, total ${io.engine.clientsCount} clients`
  );
  socket.emit("set_world", world);
  socket.emit("update", world);
  update_ims_table();
  socket.conn.on("close", (reason) => {
    console.log(
      `Closed connection: ${socket.id} - ${socket.conn.remoteAddress} - ${reason}`
    );
  });
});

server.listen(port, () => {
  console.info(`SocketIO server listening on *:${port}`);
});

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
    /** @type {Number[][]} List of future positions of the robot */
    this.path = [];
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

    // If data.robot_home_zones doesn't exist, then it's in the grid, so generate it from grid
    if (!data.robot_home_zones) {
      data.robot_home_zones = [];
      data.item_load_zones = [];
      data.station_zones = [];

      for (let r = 0; r < data.grid.length; r++) {
        for (let c = 0; c < data.grid[r].length; c++) {
          if (data.grid[r][c] <= 1) continue;
          // Walls are 1, Robots are 2, Item load Zones are 3, Stations are 4
          if (data.grid[r][c] == 2) {
            data.robot_home_zones.push([r, c]);
          } else if (data.grid[r][c] == 3) {
            data.item_load_zones.push([r, c]);
          } else if (data.grid[r][c] == 4) {
            data.station_zones.push([r, c]);
          }
          data.grid[r][c] = 0; // Clear the grid position now
        }
      }
    }

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

var world = World.from_yaml(
  process.env.WAREHOUSE_YAML || "./warehouses/main_warehouse.yaml"
);

console.log('World loaded...');



function point_list_compare(/** @type {Array} */ a, /** @type {Array} */ b) {
  // Assumes first list has list of lists, each containing two points
  if (a.length != b.length) {
    return false;
  }
  return a.every((val, idx) => {
    return (val instanceof Array &&
            b[idx] instanceof Array &&
            (val[0] == b[idx][0]) &&
            (val[1] == b[idx][1]));
  })
}

const MOVE_MAP = {
  'R': [1, 0],
  'L': [-1, 0],
  'U': [0, 1],
  'D': [0, -1],
  'W': [0, 0]
};

function generate_path_from_directions(start_pos, directions) {
  /** @type {Number[][]} List of future positions of the robot, not including start_pos. */
  let positions = [];
  for (let direction of directions) {
      let dx = MOVE_MAP[direction][0];
      let dy = MOVE_MAP[direction][1];
      let lastPosition = positions[positions.length - 1] ||  [start_pos.x, start_pos.y];
      positions.push([lastPosition[0] + dx, lastPosition[1] + dy]);
  }
  return positions;
}

async function update_robots(robots_data) {
  robots_data.forEach((robot, i) => {
    if (!robot) return;
    // @ts-ignore
    let pos = JSON.parse(robot.position);
    world.robots[i].pos.x = pos[0];
    world.robots[i].pos.y = pos[1];
    // @ts-ignore
    robot.id = robot.robot_id;
    // @ts-ignore
    robot.pos = { x: pos[0], y: pos[1] };
    // @ts-ignore
    robot.held_item_id = parseInt(robot.held_item_id); // NaN for empty string / no item
    if (isNaN(robot.held_item_id)) {
      // Not strictly necessary since socket.io converts to null, this guarantees it.
      robot.held_item_id = null; 
    }
    // @ts-ignore
    // Robot path is char string UDLRW of directions based on robot position
    let robot_next_path = generate_path_from_directions(robot.pos, robot.path)
    // Check if the current robot path is the same as the previous one with head popped
    let old_path_part = world.robots[i].path.slice(1);
    if (robot_next_path.length != 0 && point_list_compare(old_path_part, robot_next_path)) {
      // If so, we don't need to resend this path since the path is the same (minus head).
      // This reduces the socket message size dramatically.
      delete robot.path; // Don't send this in the io message, let visualizer use existing path.
    } else {
      robot.path = robot_next_path;
    }
    world.robots[i].path = robot_next_path;
    
  });
  let msg = { t: world.t, robots: robots_data, dt_s: world.dt_s };
  io.emit("update", msg);
}

const REDIS_QUERY_RATE_MS = 1000; // max rate to query redis DB at
var last_redis_query_ms = null;
var latest_ims_data = null;
const STATION_LIMIT = 25; // Limit number of stations emitted to 25
async function update_ims_table() {
  if (io.engine.clientsCount == 0) return; // No point updating table if no clients.
  const t_start = Date.now();

  // Check if cache hit
  if (
    last_redis_query_ms &&
    latest_ims_data &&
    Date.now() - last_redis_query_ms < REDIS_QUERY_RATE_MS
  ) {
    console.log("Returning cached ims data");
    io.emit("ims_all_orders", latest_ims_data);
    return;
  }

  // Use a pipeline to batch up redis calls and reduce networking
  const r_multi = r_client.multi();

  var ims_data = {};

  // Get up to the oldest 10 new orders from the queue [0 - 9] = 10 entries
  r_multi.lRange("orders:new", 0, 9);
  // Get up to the latest 10 finished orders
  r_multi.xRevRange("orders:finished", "+", "-", { COUNT: 10 });

  // Get busy/free station info etc.
  r_multi.lRange("stations:free", 0, STATION_LIMIT);
  r_multi.sRandMemberCount("stations:busy", STATION_LIMIT);
  r_multi.lLen("orders:new");
  r_multi.get("order:count");
  r_multi.get("station:count");
  const [
    new_order_keys,
    finished_orders_raw,
    free_station_keys,
    busy_station_keys,
    new_order_count,
    total_order_count,
    station_count,
  ] = await r_multi.exec();

  var finished_orders = [];
  if (finished_orders_raw) {
    // @ts-ignore
    finished_orders = finished_orders_raw.map((order) => {
      if (!order.message.items) {
        order.message.status = "ERROR";
        return order.message;
      }
      order.message.items = JSON.parse(order.message.items);
      order.message.created = parseFloat(order.message.created) * 1000.0; // Make ms also
      order.message.assigned = parseFloat(order.message.assigned) * 1000.0; // Make ms also
      order.message.finished = parseInt(order.id); // Make ms
      order.message.status = "COMPLETE";
      return order.message;
    });
  }

  // ims_data["new_order_keys"] = new_order_keys;
  ims_data["finished_orders"] = finished_orders;
  ims_data["free_station_keys"] = free_station_keys; // set to list
  ims_data["busy_station_keys"] = busy_station_keys;
  ims_data["station_count"] = station_count;
  ims_data["new_order_count"] = new_order_count;
  ims_data["finished_order_count"] =
    // @ts-ignore
    parseInt(total_order_count) - parseInt(new_order_count) - busy_station_keys.length;

  // Using the keys, get the order info for new orders
  if (new_order_keys) {
    const r_multi = r_client.multi();
    // @ts-ignore
    new_order_keys.forEach((order_key) => {
      r_multi.hGetAll(order_key);
    });
    const new_orders = await r_multi.exec();
    ims_data["new_orders"] = new_orders.map((order) => {
      // @ts-ignore
      if (!order || !order.items) return order;
      // @ts-ignore
      order.items = JSON.parse(order.items);
      return order;
    });
  }
  // Get Stations (and any orders they contain)
  //  the station info for the busy stations
  if (busy_station_keys) {
    const r_multi = r_client.multi();
    // @ts-ignore
    busy_station_keys.forEach((station_key) => {
      r_multi.hGetAll(station_key);
    });
    const busy_stations = await r_multi.exec();

    // Order busy stations
    ims_data["busy_stations"] = busy_stations.map((station, idx) => {
      // @ts-ignore
      station.station_id = busy_station_keys[idx].split(":")[1];
      // @ts-ignore
      if (station.items_in_station) {
        // @ts-ignore
        station.items_in_station = JSON.parse(station.items_in_station);
      }
      // @ts-ignore
      if (station.items_in_order) {
        // @ts-ignore
        station.items_in_order = JSON.parse(station.items_in_order);
      }
      return station;
    });
  }
  // Around 13-15ms locally
  console.log(`ims redis queries took ${Date.now() - t_start} ms`);

  // console.log(ims_data);
  last_redis_query_ms = t_start;
  latest_ims_data = ims_data;
  io.emit("ims_all_orders", ims_data);
}

// Set up Redis
console.log('Setting up redis...');
const REDIS_HOST = process.env.REDIS_HOST || "localhost";
const REDIS_PORT = parseInt(process.env.REDIS_PORT || "6379");

/** @type{redis.RedisClientType} */
var r_client;

// Start the main loop listening to a redis stream and pushing out on socket to clients.
(async () => {
  console.log(`Trying to connect to redis server ${REDIS_HOST}:${REDIS_PORT}`);
  // Set up redis client
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
    if (err.code != "ECONNREFUSED") console.warn("Redis error:", err);
  });
  await r_client.connect(); // Wait for connection

  let dt_s = await r_client.hGet("states", "dt_sec");
  if (dt_s) {
    world.dt_s = parseFloat(dt_s);
    console.info(`Loaded world dt_s = ${world.dt_s} from redis`);
  }

  console.log(
    `Redis listening to world:state stream on ${REDIS_HOST}:${REDIS_PORT}`
  );

  while (true) {
    let stream = await r_client.xRead(
      redis.commandOptions({ isolated: true }),
      [
        {
          key: "world:state",
          id: "$",
        },
      ],
      { BLOCK: 0, COUNT: 1 }
    );
    if (!stream) continue;
    if (io.engine.clientsCount == 0) continue; // No point processing if no clients
    let msg = stream[0].messages[0]; // Get first and only message
    // let msg_timestamp = msg.id;
    world.t = parseInt(msg.message.t);
    let robots_data = JSON.parse(msg.message.robots);
    update_robots(robots_data);
    update_ims_table();
  }
})();