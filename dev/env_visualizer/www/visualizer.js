// @ts-check

function Point(/** @type {number} */ x, /** @type {number} */ y) {
  this.x = x;
  this.y = y;
}
// const grid_dims = new Point(8, 8);
var grid = null;
var world = null;
const TILE_SIZE = 60;

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
    let item_name = world.item_names[idx % world.item_names.length];
    if (item_name == undefined) {
      console.error(`undefined item name for item load zone ${idx}`);
    }
    const hover_label = createSVGElement("title");
    hover_label.textContent = `Item Load Zone ${idx}`;
    zone = drawSpecialZone(zone.x, zone.y, "item_load_zone", `${item_name}s`);
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
      `Bot-${robot.id}`,
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
    if (robot.held_item_id != null) {
      if (
        world.item_names[robot.held_item_id % world.item_names.length] ==
        undefined
      ) {
        console.error(
          `undefined item name: ${robot.held_item_id} for ${robot}`
        );
      } else {
        item_name =
          world.item_names[robot.held_item_id % world.item_names.length];
      }
    }

    // Hard-coded use 3rd child element [circle, robot label, held item label]
    let svg_held_item = svg_robot.children[2];
    svg_held_item.textContent = item_name;
    
    // Update path only if it exists.
    if (robot.robot_id in saved_robot_paths) {
      // Assumes path index is same as robots
      let svg_path = paths_svg.children[idx];
      let curr_path = [[robot_interp_tile_pos.x, robot_interp_tile_pos.y]];
      curr_path = curr_path.concat(saved_robot_paths[robot.robot_id]);
      updatePath(svg_path, curr_path);
    }
    
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
    if (itemQuantities[idx] == 0) return; // Don't add cell for 0 quantitiy items
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
    statusCell.textContent = "OPEN"; // Hard-coded for now since redis new orders can only be open.
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
    // Hard-coded for now since redis finished orders can only exist if complete.
    statusCell.textContent = order.status;
    if (order.status == "COMPLETE") {
      statusCell.setAttribute("class", "complete");
    } else if (order.status == "ERROR") {
      statusCell.setAttribute("class", "failed");
    }
    row.appendChild(statusCell);

    // created
    const createdCell = document.createElement("td");
    createdCell.textContent = new Date(order.created).toLocaleString();
    row.appendChild(createdCell);

    // assigned
    const assignedCell = document.createElement("td");
    if (order.assigned)
      assignedCell.textContent = new Date(order.assigned).toLocaleTimeString();
    row.appendChild(assignedCell);

    // finished
    const finishedCell = document.createElement("td");
    finishedCell.textContent = new Date(order.finished).toLocaleTimeString();
    row.appendChild(finishedCell);

    // processing time
    const processTimeCell = document.createElement("td");
    if (order.assigned) {
      const waitTimeMs = order.assigned - order.created;
      const processTimeMs = order.finished - order.assigned;
      const totalTimeMs = waitTimeMs + processTimeMs;
      processTimeCell.textContent = `${(waitTimeMs / 1000).toFixed(0)}s + ${(
        processTimeMs / 1000
      ).toFixed(0)}s = ${(totalTimeMs / 1000).toFixed(0)}s`;
    } else {
      const processTimeMs = order.finished - order.created;
      processTimeCell.textContent = `${(processTimeMs / 1000).toFixed(0)}s`;
    }
    row.appendChild(processTimeCell);

    tableBody.appendChild(row);
  });
}

function updateStationOrderTable(table, station_orders) {
  const tableBody = table.querySelector("tbody");
  tableBody.innerHTML = "";

  // Only show first 25 stations
  station_orders.slice(0, 25).forEach((entry, idx) => {
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

    // Items In Station
    const itemsCompletedCell = document.createElement("td");
    if (entry.station_item_names) {
      itemsCompletedCell.appendChild(
        createItemCellTable(
          entry.station_item_names,
          entry.station_item_quantities,
          "complete"
        )
      );
    }
    row.appendChild(itemsCompletedCell);

    // Items In Order
    const itemsNeededCell = document.createElement("td");
    if (entry.order_item_names) {
      itemsNeededCell.appendChild(
        createItemCellTable(entry.order_item_names, entry.order_item_quantities)
      );
    }
    row.appendChild(itemsNeededCell);

    tableBody.appendChild(row);
  });
}

function updateCounts(new_orders, finished_orders) {
  const new_order_count_elem = document.getElementById("new_order_count");
  const finished_order_count_elem = document.getElementById(
    "finished_order_count"
  );
  if (new_order_count_elem) {
    new_order_count_elem.textContent = new_orders || "-";
  }
  if (finished_order_count_elem) {
    finished_order_count_elem.textContent = finished_orders || "-";
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
  update_world_info_text(world);
});

var latest_msg;

var t_start;
var curr_robots;
// Keep track of paths of robots, in case update messages don't contain them, we use saved ones
// popping the head every update step. 
var saved_robot_paths = {};
// Tracks if the t between the last and latest msg is incremented by 1
// so animation knows to tween between the two or not.
var no_missed_msgs = false;
socket.on("update", (/** @type {any} */ msg) => {
  // if (!document.hasFocus()) {
  //   // Skip Updating visuals when window not in focus
  //   return;
  // }
  // msg is list of x/y positions [{x:..., y:...}, ...] for each robot
  // console.debug("Updating world state", msg);
  prev_robots = curr_robots;
  curr_robots = msg.robots;

  if (latest_msg && msg.t && latest_msg.t && msg.t - latest_msg.t == 1) {
    no_missed_msgs = true;
  } else {
    no_missed_msgs = false;
  }
  latest_msg = msg;
  t_start = Date.now();
  if (msg.t != null) {
    update_time_text(msg.t);
  }
  // Pop the head off of any existing saved robot paths, since we had an update.
  for (let robot_id in saved_robot_paths) {
    saved_robot_paths[robot_id] = saved_robot_paths[robot_id].slice(1);
  }
  // Update saved robot paths if a robot path exists in the message
  msg.robots.forEach(robot => {
    if ('path' in robot) {
      saved_robot_paths[robot.robot_id] = robot.path;
    }
  })
  update_robot_table(msg.robots);
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
var latest_ims_msg;
socket.on("ims_all_orders", (/** @type {any} */ data) => {
  latest_ims_msg = data;
  const new_orders = data.new_orders;
  const finished_orders = data.finished_orders;
  // Create stations
  const stations_dict = {};
  if (data.free_station_keys) {
    data.free_station_keys.forEach((key) => {
      let station_id = key.split(":")[1];
      return (stations_dict[key] = { station_id: station_id });
    });
  }
  data.busy_stations.forEach((station) => {
    stations_dict[station.station_id] = station;
  });
  const stations = Object.values(stations_dict);
  // Order stations by ID
  stations.sort(
    (station_a, station_b) =>
      parseInt(station_a.station_id) - parseInt(station_b.station_id)
  );

  updateCounts(data.new_order_count, data.finished_order_count);
  // new Date(parseFloat(data.new_orders[0].created * 1000))
  // If world exists and has item_names set, add item names to order items
  if (world) {
    new_orders.forEach((order) => {
      order.item_ids = Object.keys(order.items);
      order.item_quantities = Object.values(order.items);
      order.item_names = order.item_ids.map(
        (item_id) => world.item_names[item_id % world.item_names.length]
      );
    });
    stations.forEach((station) => {
      if (station.order) station.order_id = station.order.split(":")[1];
      // Items in station
      if (station.items_in_station) {
        station.station_item_ids = Object.keys(station.items_in_station);
        station.station_item_quantities = Object.values(
          station.items_in_station
        );
        station.station_item_names = station.station_item_ids.map(
          (item_id) => world.item_names[item_id % world.item_names.length]
        );
      }
      if (station.items_in_order) {
        station.order_item_ids = Object.keys(station.items_in_order);
        station.order_item_quantities = Object.values(station.items_in_order);
        station.order_item_names = station.order_item_ids.map(
          (item_id) => world.item_names[item_id % world.item_names.length]
        );
      }
    });
  }
  updateNewOrderTable(newOrderTable, new_orders);
  updateFinishedOrderTable(finishedOrderTable, finished_orders);
  updateStationOrderTable(stationOrderTable, stations);
});

function update_robot_table(robots) {
  // Robot ID
  // Held Item
  // Task
  // Status
  // Get a reference to the table body
  const tbody = document.querySelector("#robot_table tbody");
  if (!tbody) return;

  // Clear out any existing rows
  tbody.innerHTML = "";

  // Add a new row for each robot, first 25 robots only.
  robots.slice(0, 25).forEach((robot) => {
    const row = document.createElement("tr");

    // Function to create a cell and add it to the row
    const addCell = (text) => {
      const cell = document.createElement("td");
      cell.textContent = text;
      row.appendChild(cell);
    };

    // Robot ID
    addCell(robot.robot_id);
    // Held Item
    let held_item_name = "";
    if (robot.held_item_id != null)
      held_item_name =
        world.item_names[robot.held_item_id % world.item_names.length];
    addCell(held_item_name);
    // Task
    let task_description = "";
    if (robot.task_key) {
      const taskComponents = robot.task_key.split(":"); // task:station:4:order:104:0:2
      const [_a, _b, stationId, _c, orderId, itemId] = taskComponents;
      let item_name = world.item_names[itemId % world.item_names.length];
      task_description = `Move item ${item_name} to station ${stationId} for order ${orderId}`;
    }
    addCell(task_description);
    // Status / State Description
    addCell(robot.state_description);

    // Add the row to the table
    tbody.appendChild(row);
  });
}

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
  if (!no_missed_msgs) {
    t = 1; // Only tween if no missed messages between prev msg and current.
  } else if (latest_msg.dt_s) {
    t = (Date.now() - t_start) / (parseFloat(latest_msg.dt_s) * 1000.0);
    if (t > 1) {
      return; // No more changes, no need to update
    }
    t = Math.max(Math.min(t, 1.0), 0.0);
  }
  svg_update_robots(latest_msg.robots, t);
}, ANIMATION_UPDATE_RATE_MS);

function update_time_text(t) {
  let tblock = document.getElementById("time");
  if (!(tblock instanceof HTMLSpanElement)) {
    throw Error("Missing time paragraph element.");
  }
  let time_str = Date().toLocaleString() + " T=" + t;
  tblock.textContent = time_str;
}

function update_world_info_text(world) {
  /** Updates the world_info text element with world size, # robots, etc. */
  let infoblock = document.getElementById("world_info");
  if (!(infoblock instanceof HTMLSpanElement)) {
    throw Error("Missing world_info element.");
  }
  let info_str =
    `World Size: ${world.grid.length} x ${world.grid[0].length}, ${world.robots.length} Robots, ` +
    `${world.item_load_positions.length} Item load zones, ` +
    `${world.station_positions.length} Stations`;
  infoblock.textContent = info_str;
}