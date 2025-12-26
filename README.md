# EdgeAI Smart Parking System 

An **EdgeAI-enabled Smart Parking System** that reduces redundant IoT data transmission using lightweight machine learning, while maintaining accurate real-time parking occupancy updates.  
The project demonstrates how **predictive intelligence at the edge** can significantly improve scalability, bandwidth efficiency, and operational cost in smart parking deployments.

---

## Problem Statement

Traditional IoT-based smart parking systems continuously transmit parking slot status, even when no change occurs. Since parking slots often remain empty or occupied for long periods, this results in:

- Redundant data transmission  
- High bandwidth and cloud costs  
- Increased power consumption  

This project addresses these challenges using **prediction-based transmission suppression**.

---

## Proposed Solution

Instead of transmitting every sensor update, the system:

1. Predicts whether a parking slot’s state is **stable or likely to change**
2. Transmits data **only when meaningful changes are expected**
3. Suppresses redundant “no-change” messages

All decisions are made at the **edge**, enabling future deployment on low-power microcontrollers such as the ESP32.

---

## System Architecture

Sensor Data → Feature Engineering → ML Stability Prediction → EdgeAI Suppression Logic → MQTT → Live Dashboard


### Core Components

- **Sensor Features (Offline Dataset)**
  - Magnetometer statistics
  - Time-of-Flight (ToF) distance metrics
  - Temporal differences

- **Machine Learning Models**
  - Logistic Regression
  - Decision Tree (selected for TinyML readiness)

- **EdgeAI Suppression Logic**
  - Actual state change → transmit
  - Predicted state change → transmit
  - Stable state → suppress

- **Communication**
  - MQTT publish/subscribe model

- **Visualization**
  - Real-time Streamlit dashboard

---

## Dataset & Feature Engineering

- Multiple CSV datasets collected (~200 readings each)
- Data recorded for different vehicle types and positions
- Engineered features include:
  - Sliding-window min/mean statistics
  - Magnetic norm and derivatives
  - ToF distance metrics and temporal changes

Ground-truth occupancy labels were derived using distance thresholds for supervised learning.

---

## Data Collection

Sensor data was collected using a physical parking-slot sensing setup consisting of a magnetometer and a Time-of-Flight (ToF) distance sensor. Each data file represents approximately 200 sequential readings captured over time for a single parking scenario.

Data was collected under multiple real-world conditions to ensure robustness, including:
- Different vehicle types (e.g., small and mid-sized cars)
- Varying vehicle positions within the parking slot (left, center, right)
- Transitions between empty and occupied states

Each raw dataset was stored as a CSV file containing timestamped sensor readings. These files serve as the ground truth input for feature engineering and supervised machine learning.

The collected data reflects realistic parking behavior, including long stable periods and brief transition events, making it suitable for evaluating transmission suppression strategies.


---

## Data Preprocessing

The raw sensor datasets were preprocessed to convert noisy, low-level sensor readings into structured feature vectors suitable for machine learning.

Preprocessing steps included:
- Timestamp alignment and sorting
- Removal of corrupted or incomplete records
- Normalization of sensor values using a standard scaler
- Sliding-window aggregation to compute statistical features

Key engineered features include:
- Minimum and mean magnetometer readings
- Magnetic field norm and temporal differences
- Minimum and mean ToF distance values
- First-order temporal derivatives to capture motion trends

Ground-truth occupancy labels were generated using a distance-based threshold on ToF measurements, allowing the formulation of a supervised classification problem.

The final output of preprocessing is a consolidated `features.csv` file, which is used consistently for model training, simulation, and evaluation.


---

## Model Performance

### Logistic Regression
- Accuracy: **97%**
- ROC-AUC: **0.9984**

### Decision Tree (Selected Model)
- Accuracy: **97%**
- ROC-AUC: **0.9994**
- Compact, fast, and suitable for TinyML deployment

---

## Transmission Reduction Results

Using EdgeAI-based suppression:

- Traditional transmissions: **1000**
- EdgeAI transmissions: **483**
- Reduction achieved: **51.7%**

Over half of all messages were intelligently suppressed without losing critical state updates.

---

## Real-Time Dashboard

The Streamlit dashboard provides:

- Live occupancy status
- Prediction probability graphs
- CHANGE and PRED_CHANGE event logs
- Global transmission metrics
- Raw MQTT message inspection

The dashboard works seamlessly with both the simulator and future hardware-based publishers.

---

## How to Run the Project

### Prerequisites
- Python 3.9+
- Mosquitto MQTT broker

```
Step 1: Start MQTT Broker
sudo service mosquitto start

Verify broker is running:
mosquitto_sub -t "test/topic"


Step 2: Start the Streamlit Dashboard
streamlit run streamlit_dashboard.py

This launches the dashboard at:
http://localhost:8501 


Step 3: Run the EdgeAI Simulator
In a new terminal:
python3 edge_simulator.py
```

---

## Technologies Used

- Python
- scikit-learn
- MQTT (Mosquitto)
- Streamlit & Plotly
- EdgeAI / TinyML concepts
- ESP32 (planned deployment)

---

## Project Structure

```
├── edge_simulator.py # EdgeAI transmission suppression simulator
├── streamlit_dashboard.py # Real-time dashboard
├── mqtt_shared.py # Shared MQTT message queue
├── features.csv # Preprocessed feature dataset
├── stability_model.pkl # Trained ML model
├── stability_scaler.pkl # Feature scaler
└── README.md
```


---

## Future Work

- Convert trained model to TinyML using micromlgen
- Deploy inference on ESP32 hardware
- Compute features directly from live sensor data
- Perform hardware-in-the-loop validation
- Measure power consumption and latency

---

## Key Takeaways

- Edge-based prediction significantly reduces IoT communication overhead
- Lightweight ML models are sufficient for real-time stability prediction
- EdgeAI improves scalability, efficiency, and sustainability of smart parking systems
