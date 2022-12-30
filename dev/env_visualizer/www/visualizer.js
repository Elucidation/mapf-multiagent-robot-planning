// @ts-check

// @ts-ignore
var socket = io();

var form = document.getElementById('form');
if (!(form instanceof HTMLFormElement))
  throw Error('Missing form element.');
var input = document.getElementById('input');

form.addEventListener('submit', function (e) {
  if (!(input instanceof HTMLInputElement))
    throw Error('Missing input element.');
  e.preventDefault();
  if (input.value) {
    socket.emit('chat message', input.value);
    input.value = '';
  }
});


var messages = document.getElementById('messages');
socket.on('chat message', function (/** @type {string | null} */ msg) {
  if (messages == null)
    throw Error('Missing messages element.');
  if (msg?.startsWith('test')) {
    //ex. test 1 2 1 3 1 1 5 2 3 2 6 4
    let parts = msg.split(' ').slice(1);
    let vals = parts.map(x => parseInt(x));
    console.log(parts, vals);
    if (vals.length % 2 != 0) {
      console.error('Wrong number of ints', vals);
    }
    else {
      let positions = []
      for (let i = 0; i < vals.length; i += 2) {
        let pos = new Point(vals[i], vals[i+1]);
        positions.push(pos);
      }
      update_positions(positions);
    }
  }
  var item = document.createElement('li');
  item.textContent = msg;
  messages.appendChild(item);
  window.scrollTo(0, document.body.scrollHeight);
});

var grid = { x: 8, y: 8 }

var canvas = document.getElementById('canvas');
if (!(canvas instanceof HTMLCanvasElement)) {
  throw Error('Missing canvas element.');
}
var context = canvas.getContext('2d');

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
    context.lineTo(x, 400);
  }

  const h = canvas.height - 2
  for (var y = 1; y < canvas.height; y += h / grid.y) {
    context.moveTo(0, y);
    context.lineTo(400, y);
  }
  context.stroke();
  context.closePath();
}

/**
 * @param {number} r row
 * @param {number} c col
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

drawBoard();

function Point(x, y) {
  this.x = x;
  this.y = y;
}

var current_positions = [];

function update_positions(new_positions) {
  current_positions.forEach(pos => {
    drawCircle(pos.x, pos.y, '', true);
  });

  new_positions.forEach(pos => {
    drawCircle(pos.x, pos.y);
  });
  current_positions = new_positions;
}

update_positions([new Point(1, 1), new Point(3, 5)]);
