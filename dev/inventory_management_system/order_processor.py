import paho.mqtt.client as mqtt
import time
import json
import datetime
from database_order_inserter import DatabaseOrderInserter

db_orders = DatabaseOrderInserter('orders.db')
db_orders.reset() # Clear tables

# Read MQTT order request and insert into database

# todo: create Order class to manage labels etc.

def on_message(client, userdata, message):
    timestamp = datetime.datetime.now()
    try:
        # msg = str(message.payload.decode("utf-8"))
        order = json.loads(message.payload.decode("utf-8"))
        order['created'] = timestamp
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
