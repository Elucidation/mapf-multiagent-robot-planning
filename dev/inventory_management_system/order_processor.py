import paho.mqtt.client as mqtt  # type: ignore
import json
from datetime import datetime
from database_order_manager import DatabaseOrderManager, Order
import logging
from collections import Counter
import Item
import sys

from Order import OrderId
from Station import StationId

# Set up logging
logger = logging.getLogger("order_processor_logger")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)


# Read MQTT order request and insert into database


def add_new_order(order_data: dict) -> bool:
    """
    Add a new order to the database.

    :param order_data: A dictionary containing the order data.
    :type order_data: dict

    :return: A boolean indicating the success or failure of the operation.
    :rtype: bool
    """
    order_data["created"] = datetime.now()
    items = Item.make_counter_of_items(order_data["items"])

    try:
        order = db_orders.add_order(items=items, created_by=order_data["created_by"], created=order_data["created"],
                                    description=order_data["description"], status=order_data["status"])
        logger.info("Added new order: %s", order)
        return True
    except Exception as e:
        logger.error("Failed to add order: %s", e)
        return False


def assign_order_to_station(order_id: OrderId, station_id: StationId):
    """
    Assign an order to a station.

    :param order_id: The ID of the order to be assigned.
    :type order_id: str
    :param station_id: The ID of the station to assign the order to.
    :type station_id: str

    :return: A boolean indicating the success or failure of the operation.
    :rtype: bool
    """
    if db_orders.assign_order_to_station(order_id=order_id, station_id=station_id):
        logger.info(f"Assigned Order {order_id} to Station {station_id}")
        return True
    else:
        return False


def add_item_to_station(station_id, item_id, quantity):
    """
    Add items to a station.

    :param station_id: The ID of the station to add the items to.
    :type station_id: str
    :param item_id: The ID of the item to be added.
    :type item_id: str
    :param quantity: The number of items to be added.
    :type quantity: int

    :return: A boolean indicating the success or failure of the operation.
    :rtype: bool
    """
    try:
        db_orders.add_item_to_station(
            station_id=station_id,
            item_id=item_id,
            quantity=quantity,
        )
        log_message = f"Added Item {item_id} x{quantity} to Station {station_id}"
        logger.info(log_message)
        return True
    except Exception as e:
        logger.error("Failed to add item to station: %s", e)
        return False


def on_message(client, userdata, message):
    """
    Handle incoming messages.

    :param client: The client instance.
    :type client: object
    :param userdata: The user-defined data.
    :type userdata: object
    :param message: The incoming message.
    :type message: object

    :return: A boolean indicating the success or failure of the operation.
    :rtype: bool
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
            return add_new_order(data)
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
        db_orders.reset() # Clear tables

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
