import pandas as pd

delay = 3

send_df = pd.read_csv(f"./data/sending_{delay}.csv")
receive_df = pd.read_csv(f"./data/received_{delay}.csv")

diff = receive_df["receive_time"] - send_df["send_time"]
merged = pd.merge(send_df, receive_df, on="id")
merged["difference"] = diff
merged.to_csv(f"./data/tx_rx_data_{delay}.csv", index=False)