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

# Global configure of git user and email to avoid errors when running git commands
RUN unset GIT_DIR GIT_WORK_TREE && \
    git config --global user.name "bids_bot" && \
    git config --global user.email "bids_bot@cpipstudy.ca"

ENTRYPOINT ["skullduggery"]
