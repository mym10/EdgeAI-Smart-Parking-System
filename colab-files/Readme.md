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
