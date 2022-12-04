import paho.mqtt.client as mqtt
import time
import json
from datetime import datetime
from database_order_manager import DatabaseOrderManager, Order

db_orders = DatabaseOrderManager('orders.db')
db_orders.reset() # Clear tables

# Read MQTT order request and insert into database

# todo: create Order class to manage labels etc.

def on_message(client, userdata, message):
    timestamp = datetime.now()
    try:
        # msg = str(message.payload.decode("utf-8"))
        order_data = json.loads(message.payload.decode("utf-8"))
        order_data['created'] = timestamp
        order = Order.load_from_dict(order_data)

    except Exception as e:
        order = 'corrupted'

    db_orders.add_order(order)
    print("Added order: ", order)


# Using localhost mosquitto MQTT broker (powershell: mosquitto.exe)
mqttBroker = "localhost"

client = mqtt.Client("OrderIngester")
client.connect(mqttBroker)

# client.loop_start() # spawns a thread

client.subscribe("order/requests", qos=1)
client.on_message = on_message

# time.sleep(3000)
# client.loop_stop()
client.loop_forever() # Uses main thread
