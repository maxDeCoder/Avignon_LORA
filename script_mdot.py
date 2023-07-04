import serial
import time
import argparse
import tqdm
import pandas as pd

def AT(device, command: str):
    device.write((command + "\n").encode())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", "--num_packets", dest="num_packets", help="number of packets to be sent", required=False, default=5)
    parser.add_argument("-p", "--payload", dest="payload", help="Payload to be send", required=False, default="Test message")
    parser.add_argument("-s", "--sleep", dest="sleep_for", help="Delay between each payload", required=False, default=1)
    parser.add_argument("-P", "--port", dest="port", help="port for connection to mdot", required=False, default="COM9")

    args = parser.parse_args()
    
    SERIAL_PORT = args.port
    BAUD_RATE = 115200

    num_packets = int(args.num_packets)
    payload = args.payload
    sleep_duration = int(args.sleep_for)

    print(f"connecting to mDot via {SERIAL_PORT}, baud rate = {BAUD_RATE}")
    device = serial.Serial(SERIAL_PORT, BAUD_RATE)

    AT(device, "AT")
    time.sleep(1)

    response = device.read_all()
    response = response.decode()

    if not "OK" in response:
        print("Failed to connect to mDot")
        exit()

    print("connected to mDot, AT OK")
    input("Waiting to start transmission")
    print("Starting transmission")

    tx_time = []
    for i in tqdm.tqdm(list(range(num_packets))):
        tx_time.append(int(time.time()))
        AT(device, f"AT+SEND={payload}_{sleep_duration}_{i}")
        time.sleep(sleep_duration)

    device.close()

    pd.DataFrame({"id":list(range(num_packets)), "send_time":tx_time}).to_csv(f"./data/sending_{sleep_duration}.csv", index=False)
