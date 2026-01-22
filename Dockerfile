# Start from official Python 3.12 slim image
# Slim version is smaller than full Python image but includes everything we need
FROM python:3.12-slim

# Set working directory inside the container
# All subsequent commands will run from this directory
WORKDIR /app

# Install system dependencies required by psycopg2
# psycopg2 needs PostgreSQL client libraries to compile
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first
# Docker caches layers, so if requirements.txt doesn't change,
# this layer won't be rebuilt even if code changes
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces image size by not storing pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# This comes after installing dependencies so code changes don't
# trigger dependency reinstallation
COPY . .

# Expose port 8000
# This is documentation - it tells users which port the app uses
# The actual port binding happens in docker-compose
EXPOSE 8000

# Run database migrations before starting the server
# The && ensures server only starts if migrations succeed
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000