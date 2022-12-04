import paho.mqtt.client as mqtt
import json
import time
import random
from collections import Counter

# Using localhost mosquitto MQTT broker (powershell: mosquitto.exe)
mqttBroker = "localhost"
client = mqtt.Client("FakeOrderSender")
client.connect(mqttBroker)

# def on_publish(client,userdata,result):
#     pass
# client.on_publish = on_publish


# client.loop_start() # start on separate thread
for i in range(10):
    print(f'{i} - Sending')

    item_list = Counter(list(range(i)))

    # Note, # of items assumed to be low, as total message string length needs to fit MQTT message size max.
    order_request = {
        # 'order_id': auto_generated
        'created_by': 1, # user id
        # 'created': auto_generated
        'destination_id': 1,
        'description': f'lorem #{i} ipsum',
        'items' : item_list
    }
    order_request_json = json.dumps(order_request)
    ret = client.publish("order/requests", order_request_json, qos=1)
    client.loop()
    ret.wait_for_publish(timeout=1e-6)
    print(ret)
    delay = random.random()*5.0 # random 0-5 second delay
    print(f'waiting {delay} seconds')
    time.sleep(delay)
print('Done')