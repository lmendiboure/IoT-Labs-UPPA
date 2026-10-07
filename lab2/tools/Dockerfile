# One image for the lab's programs: MQTT relay/viewer, simulated plant, AC-1
# teaching endpoint, and workstation tools (Python, Paho MQTT, Mosquitto clients).
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends mosquitto-clients curl jq nano vim-tiny less \
        netcat-openbsd iputils-ping dnsutils procps \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir paho-mqtt==2.1.0 tzdata
WORKDIR /lab
COPY . /lab
ENV MQTT_HOST=relay MQTT_PORT=1884 VIEWER=http://relay:8080 WORK=/work PYTHONUNBUFFERED=1
