# Use an official Python image as the base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install curl
RUN apt-get update && apt-get install -y curl && apt-get clean

# Copy the dependency files
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Expose the health check port
EXPOSE 8080

# Define the command to run the application
CMD ["python", "net_mon/main.py"]

# Add a health check for the container
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/healthcheck || exit 1