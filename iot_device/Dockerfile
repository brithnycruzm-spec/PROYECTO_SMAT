FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir paho-mqtt requests
COPY mqtt_bridge.py .
CMD ["python", "mqtt_bridge.py"]