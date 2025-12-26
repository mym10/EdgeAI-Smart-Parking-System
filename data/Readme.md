## Data Collection

Sensor data was collected using a physical parking-slot sensing setup consisting of a magnetometer and a Time-of-Flight (ToF) distance sensor. Each data file represents approximately 200 sequential readings captured over time for a single parking scenario.

Data was collected under multiple real-world conditions to ensure robustness, including:
- Different vehicle types (e.g., small and mid-sized cars)
- Varying vehicle positions within the parking slot (left, center, right)
- Transitions between empty and occupied states

Each raw dataset was stored as a CSV file containing timestamped sensor readings. These files serve as the ground truth input for feature engineering and supervised machine learning.

The collected data reflects realistic parking behavior, including long stable periods and brief transition events, making it suitable for evaluating transmission suppression strategies.
