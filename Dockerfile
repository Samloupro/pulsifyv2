# Dockerfile for deploying MailScout on Coolify

# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install any OS-level dependencies (e.g., for DNS resolution)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY mailscout-main/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy library source and install it
COPY mailscout-main /app/mailscout-main
WORKDIR /app/mailscout-main
RUN pip install --no-cache-dir .

# Return to root of app
WORKDIR /app

# Expose port if needed (the library is CLI-based; adjust if you add a web service)
# EXPOSE 5000

# Default command: run the CLI (EmailPulsify supports -h for help)
ENTRYPOINT ["python", "-m", "EmailPulsify"]
