# Use official Python image for ARM64
FROM python:3.10-slim-bullseye

# Set working directory
WORKDIR /app

# Copy listener script
COPY listener.py .

# Expose port 9000 for socket listener
EXPOSE 9000

# Run the listener
CMD ["python", "-u", "listener.py"]
