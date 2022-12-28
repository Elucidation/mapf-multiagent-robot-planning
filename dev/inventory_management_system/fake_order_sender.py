import paho.mqtt.client as mqtt # type: ignore
import json
import time
import random
from collections import Counter
from Item import ItemCounter

# Using localhost mosquitto MQTT broker (powershell: mosquitto.exe)
mqttBroker = "localhost"
client = mqtt.Client("FakeOrderSender")
client.connect(mqttBroker)

# def on_publish(client,userdata,result):
#     pass
# client.on_publish = on_publish


# client.loop_start() # start on separate thread

fixed_item_list_options = [
    [1, 1, 2, 3],
    [2, 3, 3],
    [1, 2, 3],
    [3],
    [3, 5, 4, 4],
    [6, 4],
    [8, 8, 8, 8],
    [6, 5, 4, 7, 7, 8],
    [1, 2, 1, 3, 4, 4, 5, 2, 2],
    [1, 2, 3, 4, 5, 6, 7, 8, 9],
]

for i in range(10):
    print(f"{i} - Sending")
    item_list = ItemCounter(fixed_item_list_options[i % len(fixed_item_list_options)])

    # Note, # of items assumed to be low, as total message string length needs to fit MQTT message size max.
    order_request = {
        # 'order_id': auto_generated
        "created_by": 1,  # user id
        # 'created': auto_generated
        "destination_id": 1,
        "description": f"lorem #{i} ipsum",
        "items": item_list,
        "status": "OPEN",
    }
    order_request_json = json.dumps(order_request)
    ret = client.publish("order/requests", order_request_json, qos=1)
    client.loop()
    ret.wait_for_publish(timeout=1e-6)
    print(ret)
    delay = random.random() * 1.0  # random 0-5 second delay
    print(f"waiting {delay} seconds")
    time.sleep(delay)
print("Done")
