// @ts-check

function Point(/** @type {number} */ x, /** @type {number} */ y) {
  this.x = x;
  this.y = y;
}
// const grid_dims = new Point(8, 8);
var grid = null;
var world = null;
const TILE_SIZE = 80;

// ---------------------------------------------------
// SVG Visualizations
var robots_svg; // Stores an array of SVG elements for each robot + their labels and held items
var paths_svg; // A group containing an array of SVG elements for each robot path
var prev_robots; // Tracks previous state of robots (prior position etc.)

function createSVGElement(tagName) {
  return document.createElementNS("http://www.w3.org/2000/svg", tagName);
}

function createTile(x, y, className) {
  const tile = createSVGElement("rect");
  tile.setAttribute("x", x * TILE_SIZE);
  tile.setAttribute("y", y * TILE_SIZE);
  tile.setAttribute("width", TILE_SIZE);
  tile.setAttribute("height", TILE_SIZE);
  tile.setAttribute("class", className);
  tile.setAttribute("stroke-width", "1");
  return tile;
}

function drawSpecialZone(tileX, tileY, className, label) {
  const zone = createSVGElement("g");

  // Draw colored tile
  const tile = createTile(tileX, tileY, className);
  zone.appendChild(tile);

  // Draw label
  const labelText = createSVGElement("text");
  const fontSize = TILE_SIZE * 0.3; // Adjust the multiplier to control the font size
  labelText.setAttribute("x", tileX * TILE_SIZE + TILE_SIZE * 0.05);
  labelText.setAttribute("y", tileY * TILE_SIZE + fontSize);
  labelText.setAttribute("font-size", fontSize + "px");
  labelText.setAttribute("textLength", TILE_SIZE * 0.9);
  labelText.setAttribute("lengthAdjust", "spacingAndGlyphs");
  labelText.textContent = label;
  zone.appendChild(labelText);

  return zone;
}

function svg_create_item_zones(zones) {
  return zones.map((zone, idx) => {
    let item_name = world.item_names[idx];
    if (item_name == undefined) {
      console.error(`undefined item name for item load zone ${idx}`);
    }
    const hover_label = createSVGElement("title");
    hover_label.textContent = `Item Load Zone ${idx}`;
    zone = drawSpecialZone(zone.x, zone.y, "item_load_zone", `${item_name}`);
    zone.appendChild(hover_label);
    return zone;
  });
}

function svg_create_station_zones(zones) {
  return zones.map((zone, idx) => {
    const hover_label = createSVGElement("title");
    hover_label.textContent = `Station Zone ${idx + 1}`; // Hacky +1 for station ids
    zone = drawSpecialZone(
      zone.x,
      zone.y,
      "station_zone",
      `Station ${idx + 1}`
    );
    zone.appendChild(hover_label);
    return zone;
  });
}

function svg_create_robot_home_zones(zones) {
  return zones.map((zone, idx) => {
    const hover_label = createSVGElement("title");
    hover_label.textContent = `Robot Home ${idx}`;
    zone = drawSpecialZone(zone.x, zone.y, "robot_home_zone", `Dock ${idx}`);
    zone.appendChild(hover_label);
    return zone;
  });
}

function svg_create_robots(robots) {
  return robots.map((robot) => {
    // robot has id and pos (x,y)
    const circle = createCircle("robot");
    const circleId = `robot_${robot.id}`;
    const labelText = createCircleLabel(
      circleId,
      `Robot ${robot.id}`,
      "robot_label"
    );
    const heldItemText = createCircleLabel(
      `${circleId}_held_item`,
      "",
      "robot_held_item_label"
    );
    heldItemText.setAttribute("y", TILE_SIZE * 0.2); // Offset below
    const circleGroup = createSVGElement("g");
    circleGroup.setAttribute("circleId", circleId); // Store circleId in the group
    circleGroup.appendChild(circle);
    circleGroup.appendChild(labelText);
    circleGroup.appendChild(heldItemText);
    return circleGroup;
  });
}

function svg_update_robots(robots, t) {
  robots.forEach((robot, idx) => {
    let svg_robot = robots_svg[idx]; // Group containing the circle and labels
    let prev_robot = prev_robots[idx];
    // Get interpolated position based on t
    let robot_interp_tile_pos = interp_position(
      prev_robot.pos.x,
      prev_robot.pos.y,
      robot.pos.x,
      robot.pos.y,
      t
    );

    // SVG x,y interpolated robot position
    const x = robot_interp_tile_pos.x * TILE_SIZE + TILE_SIZE / 2;
    const y = robot_interp_tile_pos.y * TILE_SIZE + TILE_SIZE / 2;

    // Move the circle group
    svg_robot.setAttribute("transform", `translate(${x}, ${y})`);

    // Update held items if it exists
    let item_name = "-";
    if (robot.held_item_id != undefined) {
      if (world.item_names[robot.held_item_id] == undefined) {
        console.error(
          `undefined item name: ${robot.held_item_id} for ${robot}`
        );
      } else {
        item_name = world.item_names[robot.held_item_id];
      }
    }

    // Hard-coded use 3rd child element [circle, robot label, held item label]
    let svg_held_item = svg_robot.children[2];
    svg_held_item.textContent = item_name;

    // Assumes path index is same as robots
    let svg_path = paths_svg.children[idx];
    let robot_path = undefined;
    if (robot.path) {
      // Add current robot position to head of path
      robot_path = [[robot_interp_tile_pos.x, robot_interp_tile_pos.y]].concat(
        robot.path
      );
    }
    updatePath(svg_path, robot_path);
  });
}

function interp_position(X1, Y1, X2, Y2, t) {
  const X = X1 + (X2 - X1) * t;
  const Y = Y1 + (Y2 - Y1) * t;
  return { x: X, y: Y };
}

function createCircle(className) {
  const circle = createSVGElement("circle");
  const radius = Math.min(TILE_SIZE / 2, TILE_SIZE / 2) * 0.8;

  circle.setAttribute("r", radius);
  circle.setAttribute("class", className);

  return circle;
}

function createCircleLabel(tag, text, className) {
  const labelText = createSVGElement("text");
  labelText.setAttribute("id", tag + "-label");
  labelText.setAttribute("font-size", TILE_SIZE * 0.2 + "px"); // Adjust the multiplier to control the font size
  labelText.setAttribute("text-anchor", "middle");
  labelText.setAttribute("class", className);
  labelText.textContent = text;
  return labelText;
}

// Create paths for each robot, all under a group
function svg_create_paths(robots) {
  const pathGroup = createSVGElement("g");
  pathGroup.setAttribute("id", "robot_paths");
  robots.map((robot) => {
    const circleId = `robot_${robot.id}`;
    pathGroup.appendChild(createPath(circleId));
  });
  return pathGroup;
}

function createPath(tag) {
  const path = createSVGElement("path");
  path.setAttribute("id", tag + "-path");
  path.setAttribute("d", ""); // Path data to be
  path.setAttribute("class", "robot_path");
  return path;
}

function updatePath(path, coordinates) {
  if (coordinates == null || coordinates == undefined) {
    return;
  }
  const pathData = coordinates
    .map((coord, index) => {
      const x = coord[0] * TILE_SIZE + TILE_SIZE / 2;
      const y = coord[1] * TILE_SIZE + TILE_SIZE / 2;
      return (index === 0 ? "M" : "L") + x + "," + y;
    })
    .join(" ");

  path.setAttribute("d", pathData);
}

function generateGridSVG(gridData) {
  const svg = createSVGElement("svg");
  const gridWidth = gridData[0].length;
  const gridHeight = gridData.length;
  svg.setAttribute("width", gridWidth * TILE_SIZE);
  svg.setAttribute("height", gridHeight * TILE_SIZE);

  for (let y = 0; y < gridHeight; y++) {
    for (let x = 0; x < gridWidth; x++) {
      const tileType = gridData[y][x];
      let className = "empty";
      if (tileType === 1) {
        className = "wall";
      }
      const tile = createTile(x, y, className);
      svg.appendChild(tile);
    }
  }

  return svg;
}

const gridContainer = document.getElementById("grid-container");
if (gridContainer == null) {
  throw Error("Missing grid-container element.");
}

function setGridSVG(gridData) {
  if (gridContainer == null) {
    console.error("Missing grid-container element.");
    return;
  }
  const gridSVG = generateGridSVG(gridData);

  // Remove any existing grid SVGs
  if (gridContainer.hasChildNodes()) {
    gridContainer.firstChild?.remove();
  }
  gridContainer.appendChild(gridSVG);
  return gridSVG;
}

function createItemCellTable(itemNames, itemQuantities, attrClass = "") {
  const table = document.createElement("table");
  const tr = document.createElement("tr");

  itemNames.forEach((item, idx) => {
    const itemCell = document.createElement("td");
    if (attrClass) {
      itemCell.setAttribute("class", attrClass);
    }
    itemCell.textContent = item;

    // If more than one item, add a 'xN' to the item name
    if (itemQuantities[idx] > 1) {
      const quantitySpan = document.createElement("span");
      quantitySpan.className = "quantity-color";

      quantitySpan.textContent = `x${itemQuantities[idx]}`;
      itemCell.appendChild(quantitySpan);
    }

    tr.appendChild(itemCell);
  });

  table.appendChild(tr);
  return table;
}

function updateNewOrderTable(table, orders) {
  const tableBody = table.querySelector("tbody");
  tableBody.innerHTML = "";

  orders.forEach((order) => {
    const row = document.createElement("tr");

    const idCell = document.createElement("td");
    idCell.textContent = order.order_id;
    row.appendChild(idCell);

    // items
    const itemCell = document.createElement("td");
    itemCell.appendChild(
      createItemCellTable(order.item_names, order.item_quantities)
    );
    row.appendChild(itemCell);

    const statusCell = document.createElement("td");
    statusCell.textContent = order.status;
    row.appendChild(statusCell);

    tableBody.appendChild(row);
  });
}

function updateFinishedOrderTable(table, orders) {
  const tableBody = table.querySelector("tbody");
  tableBody.innerHTML = "";

  orders.forEach((order) => {
    const row = document.createElement("tr");

    // ID
    const idCell = document.createElement("td");
    idCell.textContent = order.order_id;
    row.appendChild(idCell);

    // status
    const statusCell = document.createElement("td");
    statusCell.textContent = order.status;
    row.appendChild(statusCell);

    // created
    const createdCell = document.createElement("td");
    createdCell.textContent = new Date(order.created).toLocaleString();
    row.appendChild(createdCell);

    // finished
    const finishedCell = document.createElement("td");
    finishedCell.textContent = new Date(order.finished).toLocaleString();
    row.appendChild(finishedCell);

    // processing time
    const processTimeCell = document.createElement("td");
    const processTimeMs =
      Date.parse(order.finished) - Date.parse(order.created);
    processTimeCell.textContent = `${(processTimeMs / 1000).toFixed(0)}s`;
    row.appendChild(processTimeCell);

    tableBody.appendChild(row);
  });
}

function updateStationOrderTable(table, station_orders) {
  const tableBody = table.querySelector("tbody");
  tableBody.innerHTML = "";

  station_orders.forEach((entry) => {
    const row = document.createElement("tr");

    // Station ID
    const idCell = document.createElement("td");
    idCell.textContent = entry.station_id;
    row.appendChild(idCell);

    // If no Order ID just keep empty station ID
    if (!entry.order_id) {
      tableBody.appendChild(row);
      return;
    }

    // Order ID
    const orderIdCell = document.createElement("td");
    orderIdCell.textContent = entry.order_id;
    row.appendChild(orderIdCell);

    // Items Completed
    const itemsCompletedCell = document.createElement("td");
    if (entry.completed_item_names) {
      itemsCompletedCell.appendChild(
        createItemCellTable(
          entry.completed_item_names,
          entry.completed_item_quantities,
          "complete"
        )
      );
    }
    row.appendChild(itemsCompletedCell);

    // Items Needed
    const itemsNeededCell = document.createElement("td");
    if (entry.open_item_names) {
      itemsNeededCell.appendChild(
        createItemCellTable(entry.open_item_names, entry.open_item_quantities)
      );
    }
    row.appendChild(itemsNeededCell);

    tableBody.appendChild(row);
  });
}

function updateCounts(counts) {
  // counts dict {COMPLETE: ..., IN_PROGRESS: ..., OPEN: ...}
  const new_order_count_elem = document.getElementById("new_order_count");
  const finished_order_count_elem = document.getElementById(
    "finished_order_count"
  );
  if (new_order_count_elem) {
    new_order_count_elem.textContent = counts.OPEN || "-";
  }
  if (finished_order_count_elem) {
    finished_order_count_elem.textContent = counts.COMPLETE || "-";
  }
}

// ---------------------------------------------------
// Socket.IO related

// @ts-ignore
var socket = io();

socket.on("set_world", (/** @type {any} */ msg) => {
  console.debug("Updating grid dims", msg);
  world = msg;
  grid = msg.grid;
  let gridSVG = setGridSVG(grid); // Create tile map grid

  // Make item loading zones
  svg_create_item_zones(world.item_load_positions).forEach((zone) =>
    gridSVG.appendChild(zone)
  );

  // Make station zones
  svg_create_station_zones(world.station_positions).forEach((zone) =>
    gridSVG.appendChild(zone)
  );

  // Make robot home zones
  svg_create_robot_home_zones(world.robot_home_zones).forEach((zone) =>
    gridSVG.appendChild(zone)
  );

  // Create robots and store in global variable for use by updates
  curr_robots = world.robots;
  prev_robots = curr_robots;
  robots_svg = svg_create_robots(world.robots);
  robots_svg.forEach((robot) => gridSVG.appendChild(robot));

  paths_svg = svg_create_paths(world.robots);
  gridSVG.appendChild(paths_svg);

  svg_update_robots(world.robots, 0); // Update their initial positions and held items
});

var latest_msg;

var t_start;
var curr_robots;
socket.on("update", (/** @type {any} */ msg) => {
  // if (!document.hasFocus()) {
  //   // Skip Updating visuals when window not in focus
  //   return;
  // }
  // msg is list of x/y positions [{x:..., y:...}, ...] for each robot
  console.debug("Updating world state", msg);
  prev_robots = curr_robots;
  curr_robots = msg.robots;

  latest_msg = msg;
  t_start = Date.now();
  if (msg.t != null) {
    update_time(msg.t);
  }
});

const newOrderTable = document.getElementById("neworders");
if (newOrderTable == null) {
  throw Error("Missing newOrderTable element.");
}
const finishedOrderTable = document.getElementById("finishedorders");
if (finishedOrderTable == null) {
  throw Error("Missing finishedOrderTable element.");
}
const stationOrderTable = document.getElementById("stations");
if (stationOrderTable == null) {
  throw Error("Missing stationOrderTable element.");
}

var counts;
socket.on("ims_all_orders", (/** @type {any} */ all_orders) => {
  const new_orders = all_orders["new"];
  const finished_orders = all_orders["finished"];
  const station_orders = all_orders["station"];
  counts = all_orders["counts"];
  // If world exists and has item_names set, add item names to order items
  if (world) {
    new_orders.forEach((order) => {
      order.item_names = order.item_ids.map(
        (item_id) => world.item_names[item_id]
      );
    });
    finished_orders.forEach((order) => {
      order.item_names = order.item_ids.map(
        (item_id) => world.item_names[item_id]
      );
    });
    station_orders.forEach((order) => {
      if (order.completed_item_ids) {
        order.completed_item_names = order.completed_item_ids.map(
          (item_id) => world.item_names[item_id]
        );
      }
      if (order.open_item_ids) {
        order.open_item_names = order.open_item_ids.map(
          (item_id) => world.item_names[item_id]
        );
      }
    });
  }
  updateNewOrderTable(newOrderTable, new_orders);
  updateFinishedOrderTable(finishedOrderTable, finished_orders);
  updateStationOrderTable(stationOrderTable, station_orders);
  updateCounts(counts);
});

// ---------------------------------------------------
// Graphics Related

// Update graphics at a fixed rate based on latest message
const ANIMATION_UPDATE_RATE_MS = 20;
t_start = Date.now();
var interval = setInterval(() => {
  if (!latest_msg) {
    return;
  }
  // Update robot postions, held items, paths
  let t = 0;
  if (latest_msg.dt_s) {
    t = (Date.now() - t_start) / (latest_msg.dt_s * 1000);
    if (t > 1) {
      return; // No more changes, no need to update
    }
    t = Math.max(Math.min(t, 1.0), 0.0);
  }
  svg_update_robots(latest_msg.robots, t);
}, ANIMATION_UPDATE_RATE_MS);

function update_time(t) {
  let tblock = document.getElementById("time");
  if (!(tblock instanceof HTMLSpanElement)) {
    throw Error("Missing time paragraph element.");
  }
  tblock.textContent = t;
}
