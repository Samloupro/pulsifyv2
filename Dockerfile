# Dockerfile for deploying MailScout on Coolify

FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY mailscout-main /app
WORKDIR /app

# Install project
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Default command
ENTRYPOINT ["python", "-m", "EmailPulsify"]
