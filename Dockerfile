FROM python:3.10-slim

WORKDIR /app

# Copy package source
COPY . /app

# install git and git annex
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y git-annex && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install the package
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir .

ENTRYPOINT ["skullduggery"]
