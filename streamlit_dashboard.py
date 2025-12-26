# streamlit_dashboard.py
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import threading
import re
import pandas as pd
from collections import deque
import plotly.express as px
import paho.mqtt.client as mqtt

from mqtt_shared import msg_queue  # shared queue (persisted outside Streamlit)


# -------------------------
# basic UI refresh
# -------------------------
st.set_page_config(layout="wide", page_title="EdgeAI Smart Parking Dashboard")
st_autorefresh(interval=700, key="refresh")


# -------------------------
# helpers
# -------------------------
def init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default


# containers are dicts: slot_id -> deque
init("events", {})        # events[slot] = deque((ts,type,info), maxlen=2000)
init("pred_probs", {})    # pred_probs[slot] = deque((ts,prob), maxlen=2000)
init("occupancy", {})     # occupancy[slot] = deque((ts,state), maxlen=2000)
init("raw_log", deque(maxlen=2000))  # global raw messages
init("metrics", {"Traditional": None, "EdgeAI": None, "Reduction": None})
init("mqtt_started", False)


# -------------------------
# payload parsing (multi-slot aware)
# -------------------------
def ensure_slot_structs(slot_id: str):
    if slot_id not in st.session_state.events:
        st.session_state.events[slot_id] = deque(maxlen=2000)
    if slot_id not in st.session_state.pred_probs:
        st.session_state.pred_probs[slot_id] = deque(maxlen=2000)
    if slot_id not in st.session_state.occupancy:
        st.session_state.occupancy[slot_id] = deque(maxlen=2000)


def parse_payload(topic: str, payload: str):
    """
    Supported messages:
      - smartparking/slot{n}/event : "PRED_CHANGE: prob=0.998, ts=..."
      - smartparking/slot{n}/event : "CHANGE: state=0, ts=..."
      - smartparking/slot{n}/state : "0" or "1"
      - smartparking/metrics/transmissions: "Traditional=1000, EdgeAI=483, Reduction=51.70%"
    """
    now = pd.Timestamp.now()
    text = payload.strip()

    # detect slot id if present
    m_slot = re.search(r"slot(\d+)", topic)
    slot_id = f"slot{m_slot.group(1)}" if m_slot else "slot1"  # default fallback
    ensure_slot_structs(slot_id)

    # metrics (global)
    if topic.endswith("metrics/transmissions"):
        m = re.findall(r"(\w+)=([\d\.]+)", text)
        for k, v in m:
            if k in ("Traditional", "EdgeAI"):
                try:
                    st.session_state.metrics[k] = int(float(v))
                except Exception:
                    st.session_state.metrics[k] = v
            elif k == "Reduction":
                try:
                    st.session_state.metrics["Reduction"] = float(v)
                except Exception:
                    st.session_state.metrics["Reduction"] = v
        st.session_state.raw_log.appendleft((now, topic, text))
        st.session_state.events[slot_id].appendleft((now, "METRICS", text))
        return

    # PRED_CHANGE events
    if "PRED_CHANGE" in text:
        prob_match = re.search(r"prob=([\d\.]+)", text)
        prob = float(prob_match.group(1)) if prob_match else None
        st.session_state.pred_probs[slot_id].appendleft((now, prob))
        st.session_state.events[slot_id].appendleft((now, "PRED_CHANGE", f"prob={prob}"))
        st.session_state.raw_log.appendleft((now, topic, text))
        return

    # CHANGE event (explicit state change)
    if text.startswith("CHANGE"):
        st_match = re.search(r"state\s*=\s*(\d+)", text)
        try:
            state = int(st_match.group(1)) if st_match else None
        except Exception:
            state = None
        st.session_state.occupancy[slot_id].appendleft((now, state))
        st.session_state.events[slot_id].appendleft((now, "CHANGE", f"state={state}"))
        st.session_state.raw_log.appendleft((now, topic, text))
        return

    # raw state messages (topic ending with /state)
    if topic.endswith("/state"):
        try:
            s = int(text)
        except Exception:
            s = text
        st.session_state.occupancy[slot_id].appendleft((now, s))
        st.session_state.events[slot_id].appendleft((now, "STATE", str(s)))
        st.session_state.raw_log.appendleft((now, topic, text))
        return

    # fallback: store raw text
    st.session_state.raw_log.appendleft((now, topic, text))
    st.session_state.events[slot_id].appendleft((now, "MSG", text))


# -------------------------
# drain shared queue on each rerun
# -------------------------
processed = 0
while not msg_queue.empty():
    topic, payload = msg_queue.get_nowait()
    print("📥 Processing:", topic, payload)
    try:
        parse_payload(topic, payload)
    except Exception as e:
        print("❌ parse_payload error:", e)
        st.session_state.raw_log.appendleft(
            (pd.Timestamp.now(), "parse_error", f"{e} | {topic} | {payload}")
        )
    processed += 1

if processed:
    print(f"UI updated with {processed} messages")

# quick sidebar diagnostics
st.sidebar.write("Processed this run:", processed)
total_occ = sum(len(v) for v in st.session_state.occupancy.values()) if st.session_state.occupancy else 0
total_preds = sum(len(v) for v in st.session_state.pred_probs.values()) if st.session_state.pred_probs else 0
st.sidebar.write("Total occupancy samples:", total_occ)
st.sidebar.write("Total pred_probs:", total_preds)
st.sidebar.write("Known slots:", sorted(list(st.session_state.occupancy.keys())))


# -------------------------
# MQTT background thread (push-only)
# -------------------------
def on_connect(client, userdata, flags, rc):
    client.subscribe("smartparking/#")
    print("📡 MQTT subscribed to smartparking/#")


def on_message(client, userdata, msg):
    text = msg.payload.decode()
    print("🔔 MQTT received:", msg.topic, text)
    msg_queue.put((msg.topic, text))


def mqtt_thread():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect("localhost", 1883, 60)
        print("📡 MQTT connected.")
    except Exception as e:
        print("❌ MQTT connect error:", e)
        return
    client.loop_forever()


if not st.session_state.mqtt_started:
    threading.Thread(target=mqtt_thread, daemon=True).start()
    st.session_state.mqtt_started = True


# -------------------------
# UI layout
# -------------------------
st.title("🚗 EdgeAI Smart Parking Dashboard")

# live slot grid (show all known slots)
slot_ids = sorted(list(st.session_state.occupancy.keys()))
if not slot_ids:
    st.info("Waiting for slot messages... (start simulator or publish to smartparking/#)")

st.subheader("🅿️ Live Slot Grid")
if slot_ids:
    cols = st.columns(min(4, len(slot_ids)))
    for i, slot in enumerate(slot_ids):
        col = cols[i % 4]
        with col:
            latest = st.session_state.occupancy[slot][0] if st.session_state.occupancy[slot] else (None, None)
            ts, state = latest

            status = "No data"
            if state is None:
                status = "No data"
            elif state == 0:
                status = "🟩 EMPTY"
            elif state == 1:
                status = "🟥 OCCUPIED"
            else:
                status = str(state)

            st.metric(label=slot.upper(), value=status)
            if ts:
                st.write(ts.strftime("%H:%M:%S"))

st.markdown("---")

# left column: global metrics + events summary
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Transmission Metrics (global)")
    st.json(st.session_state.metrics)

    st.markdown("---")
    st.subheader("Recent Events")
    rows = []
    for slot, evq in st.session_state.events.items():
        for it in list(evq)[:6]:  # top few per slot (most recent first)
            rows.append((slot, it[0], it[1], it[2]))
    if rows:
        df_rows = pd.DataFrame(rows, columns=["slot", "ts", "type", "info"])
        df_rows["ts_str"] = df_rows["ts"].dt.strftime("%H:%M:%S")
        df_rows = df_rows.sort_values("ts", ascending=False)
        st.table(df_rows.head(12))
    else:
        st.write("No events yet.")

with col2:
    st.subheader("Prediction Probabilities")
    for slot in slot_ids:
        st.markdown(f"#### {slot.upper()}")
        preds = list(st.session_state.pred_probs.get(slot, []))
        if not preds:
            st.write("No prediction events.")
            continue
        dfp = pd.DataFrame(preds, columns=["ts", "prob"])
        dfp["time"] = dfp["ts"].dt.strftime("%H:%M:%S")
        fig = px.line(
            dfp.tail(200),
            x="time",
            y="prob",
            range_y=[0, 1],
            title=f"{slot} predicted change prob",
        )
        st.plotly_chart(fig, width="stretch")

st.markdown("---")
st.subheader("Occupancy Timelines")
for slot in slot_ids:
    st.markdown(f"##### {slot.upper()}")
    occ = list(st.session_state.occupancy.get(slot, []))
    if not occ:
        st.write("No occupancy updates.")
        continue
    df_occ = pd.DataFrame(occ, columns=["ts", "state"])
    df_occ["time"] = df_occ["ts"].dt.strftime("%H:%M:%S")
    fig_occ = px.line(
        df_occ.tail(200),
        x="time",
        y="state",
        line_shape="hv",  # step-like
        title=f"{slot} occupancy",
    )
    fig_occ.update_yaxes(tickvals=[0, 1])
    st.plotly_chart(fig_occ, width="stretch")

st.markdown("---")
st.subheader("Raw MQTT Log (most recent)")
if st.session_state.raw_log:
    df_log = pd.DataFrame(list(st.session_state.raw_log), columns=["ts", "topic", "payload"])
    df_log["ts_str"] = df_log["ts"].dt.strftime("%H:%M:%S")
    df_log = df_log.sort_values("ts", ascending=False)
    st.dataframe(df_log.head(50))
else:
    st.write("No raw messages yet.")

st.caption(
    "Tip: run mosquitto + edge_simulator.py (multi-slot) to populate this dashboard. "
    "Topics: smartparking/slot{n}/event, smartparking/slot{n}/state, smartparking/metrics/transmissions"
)
