FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/locomotive-agency/mcp-anywhere"

# Install additional system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

RUN mkdir -p /data/python-sandbox/
