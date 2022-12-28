import paho.mqtt.client as mqtt  # type: ignore
import json
from datetime import datetime
from database_order_manager import DatabaseOrderManager, Order
import logging
from collections import Counter
from Item import ItemCounter, ItemId
import sys

from Order import OrderId, OrderStatus
from Station import StationId

# Set up logging
logger = logging.getLogger("order_processor_logger")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)


# Read MQTT order request and insert into database


def add_new_order(items: ItemCounter, created_by: int, description: str, status: OrderStatus) -> bool:
    """Add a new order to the database.

    Args:
        items (ItemCounter): Counter of Item ids
        created_by (int): User id (todo: unused)
        description (str): Order description
        status (OrderStatus): Order status (open/complete etc.)

    Returns:
        bool: Success or failure to add new order
    """
    try:
        created = datetime.now()
        order = db_orders.add_order(
            items, created_by, created, description, status)
        logger.info("Added new order: %s", order)
        return True
    except Exception as e:
        logger.error("Failed to add order: %s", e)
        return False


def assign_order_to_station(order_id: OrderId, station_id: StationId) -> bool:
    """Assign an order to a station.

    Args:
        order_id (OrderId): The ID of the order to be assigned.
        station_id (StationId): The ID of the station to assign the order to.

    Returns:
        bool: success or failure
    """
    if db_orders.assign_order_to_station(order_id, station_id):
        logger.info(f"Assigned Order {order_id} to Station {station_id}")
        return True
    else:
        return False


def add_item_to_station(station_id: StationId, item_id: ItemId, quantity: int) -> bool:
    """Add items to a station.

    Args:
        station_id (StationId): The ID of the station to add the items to.
        item_id (ItemId): The ID of the item to be added.
        quantity (int): The number of items to be added.

    Returns:
        bool: success or failure
    """
    try:
        db_orders.add_item_to_station(station_id, item_id, quantity)
        log_message = f"Added Item {item_id} x{quantity} to Station {station_id}"
        logger.info(log_message)
        return True
    except Exception as e:
        logger.error("Failed to add item to station: %s", e)
        return False


def on_message(client, userdata, message) -> bool:
    """Handle incoming messages.

    Args:
        client: The client instance.
        userdata: The user-defined data.
        message: The incoming message.

    Returns:
        bool: success or failure
    """
    try:
        message_str = message.payload.decode("utf-8")
        data = json.loads(message_str)
    except json.decoder.JSONDecodeError as e:
        log_message = f"Decoding JSON of <{message.payload}> has failed, skipping"
        logger.error(log_message, e)
        return False
    except Exception as e:
        logger.error("Corrupted message, skipping: %s", e)
        return False

    try:
        if message.topic == "order/requests":
            return add_new_order(items=ItemCounter(data["items"]),
                                 created_by=data["created_by"],
                                 description=data["description"],
                                 status=data["status"])
        elif message.topic == "station/add/order":
            return assign_order_to_station(data["order_id"], data["station_id"])
        elif message.topic == "station/add/item":
            return add_item_to_station(data["station_id"], data["item_id"], data["quantity"])
    except Exception as e:
        logger.error("Error processing message: %s", e)
        return False


if __name__ == '__main__':
    db_orders = DatabaseOrderManager("orders.db")

    if 'reset' in sys.argv:
        print('Resetting database')
        db_orders.reset()  # Clear tables

    # Using localhost mosquitto MQTT broker (powershell: mosquitto.exe)
    mqttBroker = "localhost"

    client = mqtt.Client("OrderIngester")
    client.connect(mqttBroker)

    client.subscribe("order/requests", qos=1)
    client.subscribe("station/add/order", qos=1)
    client.subscribe("station/add/item", qos=1)
    client.on_message = on_message

    logger.info("Started listening...")
    client.loop_forever()  # Uses main thread
