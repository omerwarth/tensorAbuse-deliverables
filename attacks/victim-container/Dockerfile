# Use official Python image for ARM64
FROM python:3.10-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies for TensorFlow
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY build_model.py .
COPY run_victim.py .

# Build the model first, then run victim
CMD ["sh", "-c", "python -u build_model.py && python -u run_victim.py"]
