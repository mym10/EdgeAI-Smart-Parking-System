import time
import pandas as pd
import joblib
import paho.mqtt.client as mqtt

# -----------------------------------------------------------
# USER SETTINGS
# -----------------------------------------------------------
FEATURES_CSV = "features.csv"
MODEL_PATH = "stability_model.pkl"
SCALER_PATH = "stability_scaler.pkl"

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# Single-slot topics
MQTT_TOPIC_STATE = "smartparking/slot1/state"
MQTT_TOPIC_EVENT = "smartparking/slot1/event"
MQTT_TOPIC_METRICS = "smartparking/metrics/transmissions"

SEND_INTERVAL = 0.05
CHANGE_THRESHOLD_MM = 300

# -----------------------------------------------------------
# LOAD MODEL + FEATURES
# -----------------------------------------------------------
print("Loading features.csv...")
df = pd.read_csv(FEATURES_CSV, parse_dates=["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

print("Loading ML model...")
clf = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

FEATURE_COLS = [
    "g0_min","g1_min","g2_min",
    "g0_mean","g1_mean","g2_mean",
    "mag_norm","mag_norm_diff",
    "tof_min_all","tof_mean_all","tof_mean_all_diff",
]

# -----------------------------------------------------------
# PREPARE OCCUPANCY + PREDICTION
# -----------------------------------------------------------
df["occupied_now"] = (df["g1_min"] < CHANGE_THRESHOLD_MM).astype(int)

X = scaler.transform(df[FEATURE_COLS])
df["pred_prob"] = clf.predict_proba(X)[:, 1]
df["pred_label"] = (df["pred_prob"] > 0.5).astype(int)

# -----------------------------------------------------------
# MQTT SETUP
# -----------------------------------------------------------
client = mqtt.Client()
print(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT} ...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()
print("Connected!")

# -----------------------------------------------------------
# SIMULATION LOOP (single slot)
# -----------------------------------------------------------
def run_simulation(df):
    last_state = df.loc[0, "occupied_now"]
    edge_tx = 0
    trad_tx = 0

    print("\n--- Starting EdgeAI Parking Simulation (slot1) ---\n")

    for _, row in df.iterrows():
        occ = row["occupied_now"]
        pred = row["pred_label"]
        prob = row["pred_prob"]

        trad_tx += 1  # baseline system always sends

        # RULE 1: ACTUAL CHANGE
        if occ != last_state:
            last_state = occ
            edge_tx += 1

            client.publish(MQTT_TOPIC_EVENT, f"CHANGE: state={occ}, ts={row['timestamp']}")
            client.publish(MQTT_TOPIC_STATE, f"{occ}")

            print(f"[TX] CHANGE → {occ}")
            time.sleep(SEND_INTERVAL)
            continue

        # RULE 2: PREDICTED CHANGE
        if pred == 1:
            edge_tx += 1
            client.publish(MQTT_TOPIC_EVENT, f"PRED_CHANGE: prob={prob:.3f}, ts={row['timestamp']}")
            print(f"[TX] PRED_CHANGE (prob={prob:.3f})")
            time.sleep(SEND_INTERVAL)
            continue

        # RULE 3: STABLE → SUPPRESS
        time.sleep(SEND_INTERVAL)

    return edge_tx, trad_tx

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
if __name__ == "__main__":
    edge_tx, trad_tx = run_simulation(df)

    reduction = 100 * (1 - edge_tx / trad_tx) if trad_tx > 0 else 0.0
    summary = f"Traditional={trad_tx}, EdgeAI={edge_tx}, Reduction={reduction:.2f}%"

    client.publish(MQTT_TOPIC_METRICS, summary)

    print("\n=== SIMULATION COMPLETE ===")
    print(summary)

    time.sleep(1)
    client.loop_stop()
    client.disconnect()
