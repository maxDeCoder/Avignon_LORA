import paho.mqtt.client as mqtt
from random import randint
import time
import pandas as pd
import json
import base64
import os

log=len(os.listdir("./data/logs"))

broker = 'eu2.cloud.thethings.industries'
port = 1883
topic = "packet_recv"
client_id = f'client2'
username = 'first-run-vednat@vedantnetwork'
password = 'NNSXS.VBUBZYATFSBVO5VSBJ2IFZS6YBSWG4LTSMCVUWA.SJYK766J35SDV7FMF3IZYQBHYA4V7ZUJ27NNRJGGHNDKINXX736Q'
topic="v3/first-run-vednat@vedantnetwork/devices/eui-0080000000014d25/up"

df = pd.DataFrame()

previous_delay = 0
send_time = 0
receive_time = 0

def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8'))

def base64ToString(b):
    return base64.b64decode(b).decode('utf-8')

def on_message(client, userdata, msg):
    global df, send_time, receive_time, log
    received = json.loads(msg.payload.decode())
    payload = base64ToString(received["uplink_message"]["frm_payload"])
    print(payload)
    if payload=="SOT":
        return
    
    if "TIME" in payload:
        send_time = int(payload.split("=")[-1])
        return
    
    if payload=="EOT":
        receive_time = int(time.time())
        difference = receive_time-send_time
        df = pd.concat([df, pd.DataFrame({"generation time": send_time, "receive time":receive_time, "difference": difference}, index=[0])])
        return

    if "SAVE" in payload:
        payload_size, period = payload.split("_")[-2:]
        df.to_csv(f"./data/logs/log_{payload_size}_{period}.csv", index=False)
        log+=1

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