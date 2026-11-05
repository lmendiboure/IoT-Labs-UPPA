# Controlled, isolated MQTT-security exercises. Not a production image.
FROM python:3.12-slim
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
RUN apt-get update && apt-get install -y --no-install-recommends \
    mosquitto-clients openssl curl jq nano less bash netcat-openbsd procps \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir paho-mqtt==2.1.0
WORKDIR /lab
COPY . /lab
ENV MQTT_HOST=relay MQTT_PORT=1884 PYTHONUNBUFFERED=1
