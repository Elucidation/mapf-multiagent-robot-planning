// @ts-check

function Point(/** @type {number} */ x, /** @type {number} */ y) {
  this.x = x;
  this.y = y;
}
var grid_dims = new Point(8, 8);
var grid = null;
var world = null;

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
  canvas.width = 2 + 20 * grid_dims.x;
  canvas.height = 2 + 20 * grid_dims.y;
  drawBoard(world);
});

socket.on('update', (/** @type {any} */ msg) => {
  if (!document.hasFocus()) {
    // Skip Updating visuals when window not in focus
    return;
  }
  // msg is list of x/y positions [{x:..., y:...}, ...] for each robot
  console.debug('Updating world state', msg);
  updateTime(msg.t);
  update_positions(msg.positions);
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

  // Draw item loading zones
  // Todo: redraw when robots go over them.
  drawItemZones(world.item_load_positions);
}

function drawItemZones(zones) {
  zones.forEach((zone) => drawCircle(zone.x, zone.y, /* radius= */ 3, /* fill= */ 'rgb(60, 128, 86)'));
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
  var x = 20 * gx + 10 + 1;
  var y = 20 * gy + 10 + 1;
  context.beginPath()
  context.arc(x, y, radius, 0, Math.PI * 2, false);
  context.fillStyle = fill;
  context.fill();
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
  var x = 20 * gx + 10 + 1;
  var y = 20 * gy + 10 + 1;
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
  current_positions.forEach(pos => clearCircle(pos.x, pos.y));
  new_positions.forEach(pos => drawCircle(pos.x, pos.y));
  current_positions = new_positions;
}