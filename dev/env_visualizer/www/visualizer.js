// @ts-check

function Point(/** @type {number} */ x, /** @type {number} */ y) {
  this.x = x;
  this.y = y;
}
var grid = new Point(8, 8);

// ---------------------------------------------------
// Socket.IO related

// @ts-ignore
var socket = io();

socket.on('set_grid', (/** @type {Point} */ msg) => {
  console.debug('Updating grid dims', msg);
  grid.x = msg.x;
  grid.y = msg.y;
  if (context == null || !(canvas instanceof HTMLCanvasElement)) {
    console.error('Missing context or canvas elements.');
    return;
  }
  canvas.width = 2 + 20 * msg.x;
  canvas.height = 2 + 20 * msg.y;
  drawBoard();
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
function drawBoard() {
  if (context == null || !(canvas instanceof HTMLCanvasElement)) {
    console.error('Missing context or canvas elements.');
    return;
  }

  context.clearRect(0, 0, canvas.width, canvas.height);
  context.beginPath()
  context.fillStyle = "#000000";
  const w = canvas.width - 2
  for (var x = 1; x < canvas.width; x += w / grid.x) {
    context.moveTo(x, 0);
    context.lineTo(x, canvas.height);
  }

  const h = canvas.height - 2
  for (var y = 1; y < canvas.height; y += h / grid.y) {
    context.moveTo(0, y);
    context.lineTo(canvas.width, y);
  }
  context.stroke();
  context.closePath();
}

/**
 * Draw circle on canvas
 * @param {number} r row
 * @param {number} c col
 * @param {string} fill color hex
 * @param {boolean} clear if true clearRect of that circle area
 */
function drawCircle(r, c, fill = "#ff0000", clear = false) {
  if (context == null) {
    console.error('Missing context or canvas elements.');
    return;
  }
  var x = 20 * c + 10 + 1;
  var y = 20 * r + 10 + 1;
  var radius = 8;
  if (clear) {
    context.beginPath();
    context.clearRect(x - radius - 1, y - radius - 1, radius * 2 + 2, radius * 2 + 2);
    context.closePath();
  }
  else {
    context.beginPath()
    context.arc(x, y, radius, 0, Math.PI * 2, false);
    context.fillStyle = fill;
    context.fill();
    context.closePath();
  }
}

/** @type {Point[]} */
var current_positions = [];

/**
 * Draw circles for given positions, clearing old ones.
 * @param {Point[]} new_positions 
 */
function update_positions(/** @type {Point[]} */ new_positions) {
  current_positions.forEach(pos => {
    drawCircle(pos.x, pos.y, '', true);
  });

  new_positions.forEach(pos => {
    drawCircle(pos.x, pos.y);
  });
  current_positions = new_positions;
}