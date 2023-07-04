import serial
import time
import argparse
import tqdm
import pandas as pd
import threading
from random import randint

def AT(device, command: str, timeout=10):
    start_time = time.time()
    device.write((command + "\n").encode())
    response = ""
    
    while "OK" not in response:
        response = device.read_all().decode()
        if ((time.time()-start_time) > 10):
            return "TIMEOUT"

    return "OK"

def generate_packets(n, payload_length):
    def generate_payload(payload_length):
        return "".join([str(randint(0, 9)) for _ in range(payload_length)])
    
    time_of_generation = int(time.time())

    return ["SOT", f"TIME={time_of_generation}"] + [generate_payload(payload_length) for _ in range(n)] + ["EOT"], time_of_generation

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", "--num_packets", dest="num_packets", help="number of packets to be sent per update", required=False, default=5)
    parser.add_argument("-k", "--num_updates", dest="num_updates", help="number of updates to be sent", required=False, default=5)
    parser.add_argument("-l", "--payload_length", dest="payload_length", help="number of characters to be sent in every payload", required=False, default=20)
    parser.add_argument("-u", "--update_period", dest="update_period", help="How often the simulator generates new data (minutes)", required=False, default=1)
    parser.add_argument("-r", "--retries", dest="retries", help="How many times to retry a packet", required=False, default=3)
    parser.add_argument("-P", "--port", dest="port", help="port for connection to mdot", required=True)

    args = parser.parse_args()
    
    SERIAL_PORT = args.port
    BAUD_RATE = 115200

    num_packets = int(args.num_packets)
    num_updates = int(args.num_updates)
    payload_length = int(args.payload_length)
    update_period = float(args.update_period)*60
    retries = int(args.retries)

    print("num_packets:", num_packets)
    print("num_updates:", num_updates)
    print("payload_length:", payload_length)
    print("update_period:", update_period)
    print("retries:", retries)

    print(f"connecting to mDot via {SERIAL_PORT}, baud rate = {BAUD_RATE}")
    device = serial.Serial(SERIAL_PORT, BAUD_RATE)

    response = AT(device, "AT")

    if not "OK" in response:
        print("Failed to connect to mDot")
        exit()

    print("connected to mDot, AT OK")
    input("Waiting to start transmission")
    print("Starting transmission")

    tx_time = []
    for i in tqdm.tqdm(list(range(num_updates))):
        # generate new information in the form of a set of packets and also the log the time at which the 
        packets, tx = generate_packets(num_packets, payload_length)
        # log the time at which the information was generated
        tx_time.append(tx)

        # start transmission
        for payload in tqdm.tqdm(packets):
            _try = 0
            while _try <= retries:
                _try += 1
                # try to send the packet, if it fails (as indicated by the code == "ERROR" or code == "TIMEOUT") retry for <retries>
                code = AT(device, f"AT+SEND={payload}")

                # if the packet was sent then exit the loop
                if code == "OK":
                    break

        print(f"Sent {i} ")
        if i != (num_updates-1):
            time.sleep(update_period)

    AT(device, "AT+SEND=SAVE")

    device.close()
