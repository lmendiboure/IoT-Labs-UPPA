FROM python:3.12-slim
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
RUN apt-get update && apt-get install -y --no-install-recommends \
      mosquitto-clients bash curl nano less jq \
  && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir paho-mqtt==2.1.0
WORKDIR /lab
COPY . /lab
ENV PYTHONUNBUFFERED=1
