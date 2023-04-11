// @ts-check

function Point(/** @type {number} */ x, /** @type {number} */ y) {
  this.x = x;
  this.y = y;
}
const grid_dims = new Point(8, 8);
var grid = null;
var world = null;
const TILE_SIZE = 40;
const ITEM_ZONE_SIZE = 5;
const STATION_ZONE_SIZE = 10;

// ---------------------------------------------------
// Socket.IO related

// @ts-ignore
var socket = io();

socket.on("set_world", (/** @type {any} */ msg) => {
  console.debug("Updating grid dims", msg);
  world = msg;
  grid = msg.grid;
  grid_dims.x = grid[0].length;
  grid_dims.y = grid.length;
  if (context == null || !(canvas instanceof HTMLCanvasElement)) {
    console.error("Missing context or canvas elements.");
    return;
  }
  canvas.width = 2 + TILE_SIZE * grid_dims.x;
  canvas.height = 2 + TILE_SIZE * grid_dims.y;
  draw_board(world);
});

var latest_msg = undefined;
socket.on("update", (/** @type {any} */ msg) => {
  // if (!document.hasFocus()) {
  //   // Skip Updating visuals when window not in focus
  //   return;
  // }
  // msg is list of x/y positions [{x:..., y:...}, ...] for each robot
  console.debug("Updating world state", msg);
  latest_msg = msg;
  if (msg.t != null) {
    update_time(msg.t);
  }
  let positions = msg.robots.map((r) => r.pos);
  update_positions(positions);
  // Draw robot paths
  for (const robot of msg.robots) {
    draw_path(robot);
  }
  // Draw held items for the robots in those positions
  draw_robot_held_items(msg.robots);
});

// ---------------------------------------------------
// Graphics Related
var canvas = document.getElementById("canvas");
if (!(canvas instanceof HTMLCanvasElement)) {
  throw Error("Missing canvas element.");
}
var context = canvas.getContext("2d");

function update_time(t) {
  let tblock = document.getElementById("time");
  if (!(tblock instanceof HTMLSpanElement)) {
    throw Error("Missing time paragraph element.");
  }
  tblock.textContent = t;
}

/**
 * Clear canvas and draw grid.
 */
function draw_board(world) {
  if (context == null || !(canvas instanceof HTMLCanvasElement)) {
    console.error("Missing context or canvas elements.");
    return;
  }

  const w = canvas.width - 2;
  const dw = w / grid_dims.x;
  const h = canvas.height - 2;
  const dh = h / grid_dims.y;

  context.clearRect(0, 0, canvas.width, canvas.height);
  context.beginPath();

  // Draw walls
  context.fillStyle = "#555";
  for (let r = 0; r < world.grid.length; r++) {
    for (let c = 0; c < world.grid[r].length; c++) {
      const cell = world.grid[r][c];
      let x = c * dw + 1;
      let y = r * dh + 1;
      if (cell == 1) {
        // Wall
        context.fillRect(x, y, dw, dh);
      }
    }
    const element = world.grid[r];
  }

  // Draw grid lines
  context.fillStyle = "#000000";

  for (let x = 1; x < canvas.width; x += dw) {
    context.moveTo(x, 0);
    context.lineTo(x, canvas.height);
  }

  for (let y = 1; y < canvas.height; y += dh) {
    context.moveTo(0, y);
    context.lineTo(canvas.width, y);
  }

  context.stroke();
  context.closePath();

  // Note: Also redraws every robot Update
  // Draw item loading zones
  draw_item_zones(world.item_load_positions);
  // Draw station zones
  draw_station_zones(world.station_positions);
}

function draw_item_zones(zones) {
  zones.forEach((zone, idx) => {
    clear_square(zone.x, zone.y);
    draw_square(
      zone.x,
      zone.y,
      /* side= */ ITEM_ZONE_SIZE,
      /* fill= */ "rgb(60, 128, 86)"
    );
    let item_name = world.item_names[idx];
    draw_text(
      zone.x,
      zone.y,
      `${item_name}`,
      /* font= */ "12px",
      /* fill= */ "rgb(0,0,0)"
    );
  });
}

function draw_station_zones(zones) {
  zones.forEach((zone, idx) => {
    clear_square(zone.x, zone.y);
    draw_square(
      zone.x,
      zone.y,
      /* side= */ STATION_ZONE_SIZE,
      /* fill= */ "rgb(68, 54, 183)"
    );
    draw_text(
      zone.x,
      zone.y,
      `Stn  ${idx}`,
      /* font= */ "12px",
      /* fill= */ "rgb(0,0,0)"
    );
  });
}

function draw_robot_held_items(robots) {
  for (const robot of robots) {
    if (robot.held_item_id != undefined) {
      let item_name = world.item_names[robot.held_item_id];
      if (item_name == undefined) {
        console.error(
          `undefined item name: ${robot.held_item_id} for ${robot}`
        );
      }
      draw_text(
        robot.pos.x,
        robot.pos.y,
        /* text= */ `[${item_name}]`,
        /* font= */ undefined,
        /* fill= */ undefined,
        /* y_offset= */ TILE_SIZE / 4
      );
    }
  }
}

function grid_to_xy(gx, gy) {
  let x = TILE_SIZE * gx + TILE_SIZE / 2 + 1;
  let y = TILE_SIZE * gy + TILE_SIZE / 2 + 1;
  return [x, y];
}

/**
 * Draw circle on canvas
 * @param {number} gx col
 * @param {number} gy row
 * @param {number} radius radius of circle
 * @param {string} fill color hex
 */
function draw_circle(gx, gy, radius = 8, fill = "#ff0000") {
  if (context == null) {
    console.error("Missing context or canvas elements.");
    return;
  }
  let [x, y] = grid_to_xy(gx, gy);
  context.beginPath();
  context.arc(x, y, radius, 0, Math.PI * 2, false);
  context.fillStyle = fill;
  context.fill();
  context.closePath();
}

/**
 * Draw text on canvas
 * @param {number} gx col
 * @param {number} gy row
 * @param {string} text
 * @param {string} font
 * @param {string} fill color hex
 */
function draw_text(
  gx,
  gy,
  text,
  font = "12px serif",
  fill = "#ff0000",
  y_offset = -TILE_SIZE / 4
) {
  if (context == null) {
    console.error("Missing context or canvas elements.");
    return;
  }
  let [x, y] = grid_to_xy(gx, gy);
  context.font = font;
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillStyle = fill;
  context.fillText(text, x, y + y_offset);
}

/**
 * draw the future path of robot(s)
 * @param {any} robot json object with pos/held_item_id etc.
 */
function draw_path(robot, color = "rgb(206 150 231)", line_width = 2) {
  if (context == null) {
    console.error("Missing context or canvas elements.");
    return;
  }
  if (robot.path == undefined || robot.path.length == 0) {
    return; // Path empty
  }

  context.beginPath();
  context.lineWidth = line_width;
  context.strokeStyle = color;
  let [x, y] = grid_to_xy(robot.pos.x, robot.pos.y);
  context.moveTo(x, y);

  for (let i = 0; i < robot.path.length; i++) {
    let [x, y] = grid_to_xy(robot.path[i][0], robot.path[i][1]);
    context.lineTo(x, y);
  }
  context.stroke();
  context.closePath();
}

/**
 * Draw square on canvas
 * @param {number} gx col
 * @param {number} gy row
 * @param {number} side side length of square
 * @param {string} fill color hex
 */
function draw_square(gx, gy, side = 8, fill = "#ff0000") {
  if (context == null) {
    console.error("Missing context or canvas elements.");
    return;
  }
  let [x, y] = grid_to_xy(gx, gy);
  context.beginPath();
  context.rect(x - side / 2, y - side / 2, side, side);
  context.fillStyle = fill;
  context.fill();
  context.closePath();
}
/**
 * Clear square on canvas
 * @param {number} gx col
 * @param {number} gy row
 * @param {number} side side length of square
 */
function clear_square(gx, gy, side = TILE_SIZE - 2) {
  if (context == null) {
    console.error("Missing context or canvas elements.");
    return;
  }
  let [x, y] = grid_to_xy(gx, gy);
  context.beginPath();
  context.clearRect(x - side / 2, y - side / 2, side, side);
  context.closePath();
}

/**
 * Clear Rect for circle on canvas
 * @param {number} gx col
 * @param {number} gy row
 * @param {number} radius radius of circle
 */
function clear_circle(gx, gy, radius = 8) {
  if (context == null) {
    console.error("Missing context or canvas elements.");
    return;
  }
  let [x, y] = grid_to_xy(gx, gy);
  context.beginPath();
  context.clearRect(
    x - radius - 1,
    y - radius - 1,
    radius * 2 + 2,
    radius * 2 + 2
  );
  context.closePath();
}

/** @type {Point[]} */
var current_positions = [];

/**
 * Draw circles for given positions, clearing old ones.
 * @param {Point[]} new_positions
 */
function update_positions(/** @type {Point[]} */ new_positions) {
  current_positions.forEach((pos) => clear_square(pos.x, pos.y));

  // Re-draw station/item zones
  draw_item_zones(world.item_load_positions);
  draw_station_zones(world.station_positions);

  new_positions.forEach((pos, idx) => {
    draw_circle(pos.x, pos.y);
    draw_text(
      pos.x,
      pos.y,
      `Rbt ${idx}`,
      /* font= */ "12px serif",
      /* fill= */ "rgb(0,0,0)"
    );
  });
  current_positions = new_positions;
}
