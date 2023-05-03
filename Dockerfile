FROM alpine:latest
RUN apk add --no-cache py3-redis py3-numpy py3-yaml py-pip py-flask && pip install --no-cache-dir python-socketio