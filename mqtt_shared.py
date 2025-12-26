# mqtt_shared.py
import queue

# One global queue, imported by both app and MQTT thread code
msg_queue = queue.Queue()
