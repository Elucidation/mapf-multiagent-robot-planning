import paho.mqtt.client as mqtt
import time
import json
from datetime import datetime
from database_order_manager import DatabaseOrderManager, Order

db_orders = DatabaseOrderManager("orders.db")
# db_orders.reset() # Clear tables

# Read MQTT order request and insert into database

# todo: create Order class to manage labels etc.


def add_new_order(data):
    data["created"] = datetime.now()
    order = Order.load_from_dict(data)
    db_orders.add_order(order)
    print("Added order: ", order)


def assign_order_to_station(data):
    if db_orders.assign_order_to_station(
        order_id=data["order_id"], station_id=data["station_id"]
    ):
        print(f"Assigned Order {data['order_id']} to Station {data['station_id']}")


def add_item_to_station(data):
    db_orders.add_item_to_station(
        station_id=data["station_id"],
        item_id=data["item_id"],
        quantity=data["quantity"],
    )
    print(
        f"Added Item {data['item_id']} x{data['quantity']} to Station {data['station_id']}"
    )


def on_message(client, userdata, msg):
    try:
        msg_str = msg.payload.decode("utf-8")
        data = json.loads(msg_str)
    except json.decoder.JSONDecodeError as e:
        print(f"Decoding JSON of <{msg_str}> has failed, skipping: {e} ")
        return
    except Exception as e:
        print(f"Corrupted message, skipping: {e}")
        return

    try:
        if msg.topic == "order/requests":
            add_new_order(data)
        elif msg.topic == "station/add/order":
            assign_order_to_station(data)
        elif msg.topic == "station/add/item":
            add_item_to_station(data)
    except Exception as e:
        print(f'Error processing message: {repr(e)}')


# Using localhost mosquitto MQTT broker (powershell: mosquitto.exe)
mqttBroker = "localhost"

client = mqtt.Client("OrderIngester")
client.connect(mqttBroker)

# client.loop_start() # spawns a thread

client.subscribe("order/requests", qos=1)
client.subscribe("station/add/order", qos=1)
client.subscribe("station/add/item", qos=1)
client.on_message = on_message

# time.sleep(3000)
# client.loop_stop()
print("Started listening...")
client.loop_forever()  # Uses main thread
