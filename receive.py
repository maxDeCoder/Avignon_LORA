import paho.mqtt.client as mqtt
from random import randint
import time
import pandas as pd
import json
import argparse
import base64

broker = 'eu2.cloud.thethings.industries'
port = 1883
topic = "packet_recv"
client_id = f'client2'
username = 'first-run-vednat@vedantnetwork'
password = 'NNSXS.VBUBZYATFSBVO5VSBJ2IFZS6YBSWG4LTSMCVUWA.SJYK766J35SDV7FMF3IZYQBHYA4V7ZUJ27NNRJGGHNDKINXX736Q'
topic="v3/first-run-vednat@vedantnetwork/devices/eui-0080000000014d25/up"

num_data = 300

df = pd.DataFrame({"id": list(range(num_data)), "receive_time": [0]*num_data})

previous_delay = 0

def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8'))

def base64ToString(b):
    return base64.b64decode(b).decode('utf-8')

def on_message(client, userdata, msg):
    global df, previous_delay
    received = json.loads(msg.payload.decode())
    payload = base64ToString(received["uplink_message"]["frm_payload"])
    _id = int(payload.split("_")[-1])
    _delay = int(payload.split("_")[-2])

    if previous_delay != _delay:
        df.to_csv(f"./data/received_{previous_delay}.csv", index=False)
        df = pd.DataFrame({"id": list(range(num_data)), "receive_time": [0]*num_data})
        previous_delay = _delay

    df.loc[_id] = [_id, int(time.time())]

    print("id:", _id)

    if _id == (num_data-1):
        df.to_csv(f"./data/received_{_delay}.csv", index=False)
        df = pd.DataFrame({"id": list(range(num_data)), "receive_time": [0]*num_data})

def on_log(client, userdata, level, buf):
    print("log: ",buf)

def on_connect(client, userdata, flags, rc):
    print("Connected! Result code: " + str(rc))
    client.subscribe(topic)

client = mqtt.Client(client_id=f"client_{randint(0, 10000)}")
client.on_connect = on_connect
client.on_message = on_message
client.on_log=on_log
client.username_pw_set(username, password)

client.connect(broker)
client.loop_forever()