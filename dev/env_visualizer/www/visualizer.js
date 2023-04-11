// @ts-check

function Point(/** @type {number} */ x, /** @type {number} */ y) {
  this.x = x;
  this.y = y;
}
var grid_dims = new Point(8, 8);
var grid = null;
var world = null;
const TILE_SIZE = 40;
const ITEM_ZONE_SIZE = 5;
const STATION_ZONE_SIZE = 10;

// ---------------------------------------------------
// Socket.IO related

// @ts-ignore
var socket = io();

socket.on('set_world', (/** @type {any} */ msg) => {
  console.debug('Updating grid dims', msg);
  world = msg;
  grid = msg.grid;
  grid_dims.x = grid[0].length;
  grid_dims.y = grid.length;
  if (context == null || !(canvas instanceof HTMLCanvasElement)) {
    console.error('Missing context or canvas elements.');
    return;
  }
  canvas.width = 2 + TILE_SIZE * grid_dims.x;
  canvas.height = 2 + TILE_SIZE * grid_dims.y;
  drawBoard(world);
});

socket.on('update', (/** @type {any} */ msg) => {
  // if (!document.hasFocus()) {
  //   // Skip Updating visuals when window not in focus
  //   return;
  // }
  // msg is list of x/y positions [{x:..., y:...}, ...] for each robot
  console.debug('Updating world state', msg);
  if (msg.t != null) {
    updateTime(msg.t);
  }
  let positions = msg.robots.map((r) => r.pos);
  update_positions(positions);
});

// ---------------------------------------------------
// Graphics Related
var canvas = document.getElementById('canvas');
if (!(canvas instanceof HTMLCanvasElement)) {
  throw Error('Missing canvas element.');
}
var context = canvas.getContext('2d');

function updateTime(t) {
  var tblock = document.getElementById('time');
  if (!(tblock instanceof HTMLSpanElement)) {
    throw Error('Missing time paragraph element.');
  }
  tblock.textContent = t;
}

/**
 * Clear canvas and draw grid.
 */
function drawBoard(world) {
  if (context == null || !(canvas instanceof HTMLCanvasElement)) {
    console.error('Missing context or canvas elements.');
    return;
  }

  const w = canvas.width - 2;
  const dw = w / grid_dims.x;
  const h = canvas.height - 2;
  const dh = h / grid_dims.y;

  context.clearRect(0, 0, canvas.width, canvas.height);
  context.beginPath()

  // Draw walls
  context.fillStyle = "#555";
  for (let r = 0; r < world.grid.length; r++) {
    for (let c = 0; c < world.grid[r].length; c++) {
      const cell = world.grid[r][c];
      var x = c * dw + 1;
      var y = r * dh + 1;
      if (cell == 1) {
        // Wall
        context.fillRect(x, y, dw, dh);
      }

    }
    const element = world.grid[r];

  }

  // Draw grid lines
  context.fillStyle = "#000000";

  for (var x = 1; x < canvas.width; x += dw) {
    context.moveTo(x, 0);
    context.lineTo(x, canvas.height);
  }

  for (var y = 1; y < canvas.height; y += dh) {
    context.moveTo(0, y);
    context.lineTo(canvas.width, y);
  }

  context.stroke();
  context.closePath();

  // Note: Also redraws every robot Update
  // Draw item loading zones
  drawItemZones(world.item_load_positions);
  // Draw station zones
  drawStationZones(world.station_positions);
}

function drawItemZones(zones) {
  zones.forEach((zone, idx) => {
    clearSquare(zone.x, zone.y)
    drawSquare(zone.x, zone.y, /* side= */ ITEM_ZONE_SIZE, /* fill= */ 'rgb(60, 128, 86)')
    let item_name = world.item_names[idx];
    drawText(zone.x, zone.y, `${item_name}`, /* font= */ "12px", /* fill= */ 'rgb(0,0,0)')
  });
}

function drawStationZones(zones) {
  zones.forEach((zone, idx) => {
    clearSquare(zone.x, zone.y)
    drawSquare(zone.x, zone.y, /* side= */ STATION_ZONE_SIZE, /* fill= */ 'rgb(68, 54, 183)')
    drawText(zone.x, zone.y, `Stn  ${idx}`, /* font= */ "12px", /* fill= */ 'rgb(0,0,0)')
  });
}

function grid_to_xy(gx, gy) {
  var x = TILE_SIZE * gx + TILE_SIZE/2 + 1;
  var y = TILE_SIZE * gy + TILE_SIZE/2 + 1;
  return [x, y];
}

/**
 * Draw circle on canvas
 * @param {number} gx col
 * @param {number} gy row
 * @param {number} radius radius of circle
 * @param {string} fill color hex
 */
function drawCircle(gx, gy, radius = 8, fill = "#ff0000") {
  if (context == null) {
    console.error('Missing context or canvas elements.');
    return;
  }
  var [x, y] = grid_to_xy(gx, gy)
  context.beginPath()
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
function drawText(gx, gy, text, font = "12px serif", fill = "#ff0000") {
  if (context == null) {
    console.error('Missing context or canvas elements.');
    return;
  }
  var [x, y] = grid_to_xy(gx, gy)
  context.font = font;
  context.textAlign = "center"
  context.textBaseline = "middle"
  context.fillStyle = fill;
  context.fillText(text, x, y - TILE_SIZE/4);
}

/**
 * Draw square on canvas
 * @param {number} gx col
 * @param {number} gy row
 * @param {number} side side length of square
 * @param {string} fill color hex
 */
function drawSquare(gx, gy, side = 8, fill = "#ff0000") {
  if (context == null) {
    console.error('Missing context or canvas elements.');
    return;
  }
  var [x, y] = grid_to_xy(gx, gy)
  context.beginPath()
  context.rect(x-side/2, y-side/2, side, side)
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
function clearSquare(gx, gy, side = TILE_SIZE-2) {
  if (context == null) {
    console.error('Missing context or canvas elements.');
    return;
  }
  var [x, y] = grid_to_xy(gx, gy)
  context.beginPath();
  context.clearRect(x-side/2, y-side/2, side, side);
  context.closePath();
}

/**
 * Clear Rect for circle on canvas
 * @param {number} gx col
 * @param {number} gy row
 * @param {number} radius radius of circle
 */
function clearCircle(gx, gy, radius = 8) {
  if (context == null) {
    console.error('Missing context or canvas elements.');
    return;
  }
  var [x, y] = grid_to_xy(gx, gy)
  var radius = 8;
  context.beginPath();
  context.clearRect(x - radius - 1, y - radius - 1, radius * 2 + 2, radius * 2 + 2);
  context.closePath();
}

/** @type {Point[]} */
var current_positions = [];

/**
 * Draw circles for given positions, clearing old ones.
 * @param {Point[]} new_positions 
 */
function update_positions(/** @type {Point[]} */ new_positions) {
  current_positions.forEach(pos => clearSquare(pos.x, pos.y));

  // Re-draw station/item zones
  drawItemZones(world.item_load_positions);
  drawStationZones(world.station_positions);
  
  new_positions.forEach((pos, idx) => {
    drawCircle(pos.x, pos.y)
    drawText(pos.x, pos.y, `Rbt ${idx}`, /* font= */ "12px serif", /* fill= */ 'rgb(0,0,0)')
  });
  current_positions = new_positions;
}