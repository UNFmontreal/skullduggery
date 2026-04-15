FROM python:3.10-slim

WORKDIR /app

# Copy package source
COPY . /app

# Upgrade pip and install the package
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir .

ENTRYPOINT ["skullduggery"]
