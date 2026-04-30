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

# Copy requirements (stored at attacks/ root) and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all victim attack scenarios
COPY victim-container ./victim-container

# Select attack scenario at runtime using ATTACK_SCENARIO env var.
# Supported values: file_read, code_execution, shell_access
CMD ["sh", "-c", "\
SCENARIO=${ATTACK_SCENARIO:-file_read}; \
if [ \"$SCENARIO\" = \"file_read\" ]; then \
  python -u victim-container/file_read/build_model.py && \
  python -u victim-container/file_read/run_victim.py; \
elif [ \"$SCENARIO\" = \"code_execution\" ]; then \
  python -u victim-container/code_execution/build_code_execution_attack.py && \
  python -u victim-container/code_execution/run_victim_code_exec.py; \
elif [ \"$SCENARIO\" = \"shell_access\" ]; then \
  python -u victim-container/shell_access/build_shell_access_attack.py && \
  python -u victim-container/shell_access/run_victim_shell_access.py; \
else \
  echo \"Unknown ATTACK_SCENARIO: $SCENARIO\" && exit 1; \
fi"]
