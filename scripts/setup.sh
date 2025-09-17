#!/bin/bash

echo "Setting up Telco Retention Demo..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate || .venv\Scripts\activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Try to start Redis (optional)
echo "Checking Redis..."
if command -v docker &> /dev/null; then
    echo "Starting Redis in Docker..."
    docker run -d -p 6379:6379 --name redis-telco redis:latest 2>/dev/null || echo "Redis already running or Docker not available"
else
    echo "Docker not found. Demo will run without Redis (using in-memory storage)"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the demo:"
echo "1. Activate venv: source .venv/bin/activate"
echo "2. Run: python telco_retention_demo.py"