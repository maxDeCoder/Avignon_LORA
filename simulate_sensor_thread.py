import serial
import time
import argparse
import tqdm
import pandas as pd
from numpy.random import poisson
import threading
from random import randint

buffer = []
is_sending = False
exit_flag = False
random_delay = False
update_period = 0
lmb = 2.5
random_payload_length = False

def enque(item):
    global buffer, buffer_size

    if len(buffer) == buffer_size:
        print("Buffer Filled")
        buffer.pop()

    buffer.append(item)

def AT(command: str, timeout=10):
    global device
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
        if not payload_length == -1:
            return "".join([str(randint(0, 9)) for _ in range(payload_length)])
        else:
            return "".join([str(randint(0, 9)) for _ in range(randint(1, 256))])
    
    time_of_generation = int(time.time())

    return ["SOT", f"TIME={time_of_generation}"] + [generate_payload(payload_length) for _ in range(n)] + ["EOT"], time_of_generation

def sender_thread():
    global buffer, retries, device, is_sending, exit_flag

    while not exit_flag:
        if len(buffer) > 0:
            is_sending = True
            data = buffer.pop()
            # start transmission
            for payload in tqdm.tqdm(data):
                _try = 0
                while _try <= retries:
                    _try += 1
                    # try to send the packet, if it fails (as indicated by the code == "ERROR" or code == "TIMEOUT") retry for <retries>
                    code = AT(f"AT+SEND={payload}")

                    # if the packet was sent then exit the loop
                    if code == "OK":
                        break
        else:
            is_sending=False

    return

def generate_delay():
    global random_delay, update_period, lmb

    if random_delay:
        return (poisson(2.5, 1)[0] + 1) * 60
    
    return update_period

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", "--num_packets", dest="num_packets", help="number of packets to be sent per update", required=False, default=5)
    parser.add_argument("-k", "--num_updates", dest="num_updates", help="number of updates to be sent", required=False, default=5)
    parser.add_argument("-l", "--payload_length", dest="payload_length", help="number of characters to be sent in every payload (-1 for random between 1-256) (max 256)", required=False, default=20)
    parser.add_argument("-u", "--update_period", dest="update_period", help="How often the simulator generates new data (minutes) (-1 for poisson random)", required=False, default=1)
    parser.add_argument("-r", "--retries", dest="retries", help="How many times to retry a packet", required=False, default=3)
    parser.add_argument("-P", "--port", dest="port", help="port for connection to mdot", required=True)
    parser.add_argument("-b", "--buffer_size", dest="buffer_size", help="Size of the buffer", required=False, default=5)
    parser.add_argument("-L", "--lambda", dest="lmb", help="Value of Lambda for poisson distributin", required=False, default=2.5)

    args = parser.parse_args()
    
    SERIAL_PORT = args.port
    BAUD_RATE = 115200

    num_packets = int(args.num_packets)
    num_updates = int(args.num_updates)
    payload_length = int(args.payload_length)
    retries = int(args.retries)
    buffer_size = int(args.buffer_size)
    lmb = float(args.lmb)
    update_period = float(args.update_period)

    print("num_packets:", num_packets)
    print("num_updates:", num_updates)

    if not payload_length > 0:
        random_payload_length = True
        print("payload_length: random between 1-256")
    else:
        random_payload_length = False
        print("payload_length:", payload_length)
        
    if update_period == -1:
        random_delay=True
        print("update_period: poisson random between 1-3 mins")
    else:
        random_delay=False
        update_period = float(args.update_period)*60
        print("update_period:", update_period)
    print("retries:", retries)
    print("buffer size:", buffer_size)

    print(f"connecting to mDot via {SERIAL_PORT}, baud rate = {BAUD_RATE}")
    device = serial.Serial(SERIAL_PORT, BAUD_RATE)

    response = AT("AT")

    if not "OK" in response:
        print("Failed to connect to mDot")
        exit()

    print("connected to mDot, AT OK")
    input("Waiting to start transmission")
    print("Starting transmission")

    print("Starting Sender thread")
    # start sender thread
    thread = threading.Thread(target=sender_thread)
    thread.start()


    tx_time = []
    for i in range(num_updates):
        # generate new information in the form of a set of packets and also the log the time at which the 
        packets, tx = generate_packets(num_packets, payload_length)
        # log the time at which the information was generated
        tx_time.append(tx)

        # add the packets to the buffer
        print("Adding packets to buffer")
        
        enque(packets)

        delay = generate_delay()
        if i != (num_updates-1):
            print(f"wait for {delay} secs before next update is generated")
            time.sleep(delay)
    time.sleep(10)

    # the sender is still sending then wait for the thread to finish executing
    while is_sending:
        pass

    exit_flag=True

    AT("AT+SEND=SAVE")
    device.close()
