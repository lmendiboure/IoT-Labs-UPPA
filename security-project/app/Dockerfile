FROM python:3.12-slim
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
RUN http_proxy="$HTTP_PROXY" https_proxy="$HTTPS_PROXY" no_proxy="$NO_PROXY" \
    pip install --no-cache-dir paho-mqtt==2.1.0
WORKDIR /app
COPY . /app
ENV PYTHONUNBUFFERED=1
