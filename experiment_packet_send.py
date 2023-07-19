import serial
import time
import argparse
import tqdm
import pandas as pd
import numpy as np
import threading
from random import randint
from itertools import product
import paho.mqtt.client as mqtt
from random import randint
import json
import base64
import threading
import os
import sys
import winsound

log=len(os.listdir("./data/logs"))

num_logs = 30
log_after = 10
start_logging = False
broker = 'eu2.cloud.thethings.industries'
port = 1883
topic = "packet_recv"
client_id = f'client2'
username = 'first-run-vednat@vedantnetwork'
password = 'NNSXS.VBUBZYATFSBVO5VSBJ2IFZS6YBSWG4LTSMCVUWA.SJYK766J35SDV7FMF3IZYQBHYA4V7ZUJ27NNRJGGHNDKINXX736Q'
topic="v3/first-run-vednat@vedantnetwork/devices/eui-0080000000014d25/up"

current_age = 0
log_count = 0
anchor_time = 0
start_logging = False
AOI_list = []

main_df = pd.DataFrame()

# time logger setup
def logger():
    global main_df, log_after, current_age, anchor_time, num_logs, AOI_list, log_count, start_logging, stop_sending, current_pl,current_txp, current_dr

    while log_count < num_logs:
        if start_logging:
            current_time = int(time.time())
            if anchor_time == 0:
                anchor_time = current_time

            print("LOGGER: current time:", current_time)
            print("LOGGER: anchor time:", anchor_time)

            current_age += int(current_time - anchor_time)
            anchor_time = current_time
            AOI_list.append(current_age)
            log_count += 1

            print("LOGGER: logged:", current_age)
            print("LOGGER: count:", log_count)

            time.sleep(log_after)
            
    stop_sending = True
    avg_AOI = np.mean(AOI_list)
    main_df = pd.concat([main_df, pd.DataFrame({"Tx Power": current_txp, "Data rate":current_dr, "Payload size": current_pl, "Average AOI": avg_AOI}, index=[0])])
    print(f"LOGGER: Finished: power {current_txp} datarate {current_dr} payload {current_pl} average aoi {avg_AOI}")
    print(f"LOGGER: \n", main_df)
    main_df.to_csv("./data/experiment one packet/test.csv", index=False)

    frequency = 2500  # Set Frequency To 2500 Hertz
    duration = 250  # Set Duration To 1000 ms == 1 second
    winsound.Beep(frequency, duration)



# receiver setup
def receiver():
    def stringToBase64(s):
        return base64.b64encode(s.encode('utf-8'))

    def base64ToString(b):
        return base64.b64decode(b).decode('utf-8')

    def on_message(client, userdata, msg):
        global receive_time, start_logging, current_age, anchor_time
        received = json.loads(msg.payload.decode())
        payload = base64ToString(received["uplink_message"]["frm_payload"])
        send_time = int(payload.split("|")[-1])
        receive_time = int(time.time())
        difference = receive_time-send_time
        current_age = difference
        anchor_time = send_time
        print("RECEIVER THREAD: send time:", send_time)
        print("RECEIVER THREAD: receive time:", receive_time)
        print("RECEIVER THREAD: anchor time:", anchor_time)

    def on_log(client, userdata, level, buf):
        return
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

buffer = []
is_sending = False
exit_flag = False
random_delay = False
update_period = 0
lmb = 2.5
random_payload_length = False
sent = 0
current_pl, current_dr, current_txp = 0,0,0

def enque(item):
    global buffer, buffer_size

    if len(buffer) == buffer_size:
        # print("Buffer Filled")
        buffer.pop()

    buffer.append(item)

def AT(command: str, timeout=10):
    global device
    start_time = time.time()
    device.write((command + "\n").encode())
    print("MDOT:",command)
    response = ""

    while "OK" not in response:
        response = device.read_all().decode()
        if "ERROR" in response:
            print("MDOT: ERROR ", response)
            AT("AT+JOIN")
            return "ERROR"
            

        if ((time.time()-start_time) > 10):
            return "TIMEOUT"

    return "OK"

def generate_packets(n, payload_length):
    payload = "".join([str(randint(0, 9)) for _ in range(payload_length)])
    time_of_generation = int(time.time())

    return [f"{payload}|{time_of_generation}"], time_of_generation

def sender_thread():
    global buffer, retries, device, is_sending, exit_flag, sent

    while not exit_flag:
        if len(buffer) > 0:
            is_sending = True
            data = buffer.pop()
            # start transmission
            for payload in data:
                _try = 0
                while _try <= retries:
                    _try += 1
                    # try to send the packet, if it fails (as indicated by the code == "ERROR" or code == "TIMEOUT") retry for <retries>
                    code = AT(f"AT+SEND={payload}")

                    # if the packet was sent then exit the loop
                    if code == "OK":
                        break
            
            sent += 1
            print("SENDER: Sent:", sent)

        else:
            is_sending=False

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", "--num_packets", dest="num_packets", help="number of packets to be sent per update", required=False, default=10)
    parser.add_argument("-l", "--payload_length", dest="payload_length", help="number of characters to be sent in every payload (-1 for random between 1-256) (max 256)", required=False, default=10)
    parser.add_argument("-u", "--update_period", dest="update_period", help="How often the simulator generates new data", required=False, default=1)
    parser.add_argument("-r", "--retries", dest="retries", help="How many times to retry a packet", required=False, default=3)
    parser.add_argument("-P", "--port", dest="port", help="port for connection to mdot", required=True)
    parser.add_argument("-b", "--buffer_size", dest="buffer_size", help="Size of the buffer", required=False, default=5)
    parser.add_argument("-L", "--lambda", dest="lmb", help="Value of Lambda for poisson distributin", required=False, default=2.5)

    args = parser.parse_args()
    
    SERIAL_PORT = args.port
    BAUD_RATE = 115200

    # num_packets = int(args.num_packets)
    # num_updates = int(args.num_updates)
    payload_length = [181]
    retries = 3 #int(args.retries)
    buffer_size = int(args.buffer_size)
    datarates = [5] #float(args.update_period)
    update_period = int(args.update_period)
    txp = [10,15,20,27]

    # print("num_packets:", num_packets)
    # print("num_updates:", num_updates)
    print("payload_length:", payload_length)
    print("update_period:", update_period)
    print("retries:", retries)
    print("buffer size:", buffer_size)
    print("datarates:", datarates)
    print("Transmission Power:", txp, "dB")
    print("log cycle:", log_after)

    print(f"connecting to mDot via {SERIAL_PORT}, baud rate = {BAUD_RATE}")
    device = serial.Serial(SERIAL_PORT, BAUD_RATE)

    response = AT("AT")

    if not "OK" in response:
        print("Failed to connect to mDot")
        exit()

    # start sender thread
    print("Starting sender thread")
    thread = threading.Thread(target=sender_thread)
    thread.daemon=True
    thread.start()
    print("Sender thread started\n")

    # start receiver thread
    print("Starting receiver thread")
    thread = threading.Thread(target=receiver)
    thread.daemon=True
    thread.start()
    print("Started receiver thread\n")

    print("connected to mDot, AT OK")
    input("Waiting to start transmission")
    print("Starting transmission")

    setups = product(payload_length, datarates, txp)
    anchor_time = int(time.time())

    # start transmission
    tx_time = []

    for PL, DR, TXP in setups:
        current_pl, current_dr, current_txp = PL, DR, TXP
        # start logger
        print("MAIN: Starting logger thread")
        thread = threading.Thread(target=logger)
        thread.daemon=True
        thread.start()
        print("MAIN: Started logger thread")
        AT(f"AT+TXDR={DR}")
        print(f"MAIN: Changed Datarate and Spreading Factor to DR{DR}")

        AT(f"AT+TXP={TXP}")
        print(f"MAIN: Changed transmission power to {TXP} dBm")

        stop_sending = False
        start_logging = True
        while not stop_sending:
            packets, tx = generate_packets(1, current_pl)
            tx_time.append(tx)

            enque(packets)
            time.sleep(update_period)

        # reset logger
        log_count = 0
        current_age = 0
        anchor_time = 0
        AOI_list = []
        start_logging = False

    main_df.to_csv("./data/experiment one packet/test.csv", index=False)

    exit_flag=True
    device.close()
