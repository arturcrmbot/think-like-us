FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY agents/ ./agents/

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8001

# Add parent directory to Python path and set working directory
ENV PYTHONPATH="/app:${PYTHONPATH}"
WORKDIR /app/backend

# Run the server
CMD ["python", "server.py"]