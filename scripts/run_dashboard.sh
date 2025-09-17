#!/bin/bash

echo "========================================"
echo "Telco Retention Dashboard Launcher"
echo "========================================"
echo ""
echo "🚀 Starting with Docker..."
# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env with your Azure OpenAI credentials:"
    echo "AZURE_OPENAI_API_KEY=your_key"
    echo "AZURE_OPENAI_ENDPOINT=your_endpoint" 
    echo "AZURE_OPENAI_MODEL_NAME=your_model"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Stop any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up --build -d

# Wait for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check backend health
echo "🔍 Checking backend health..."
for i in {1..5}; do
    if curl -s http://localhost:8001/api/health > /dev/null; then
        echo "✅ Backend is responding!"
        break
    fi
    echo "   Attempt $i/5... waiting..."
    sleep 3
done

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services started successfully!"
    echo ""
    echo "🌐 Dashboard: http://localhost:8050"
    echo "🔧 API: http://localhost:8001/api/health"
    echo ""
    echo "📋 To view logs: docker-compose logs -f"
    echo "🛑 To stop: docker-compose down"
    
    # Open dashboard in browser
    if command -v start &> /dev/null; then
        start http://localhost:8050
    elif command -v open &> /dev/null; then
        open http://localhost:8050
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8050
    fi
else
    echo "⚠️  Services may have issues, but containers are running"
    echo "🌐 Try opening: http://localhost:8050"
    echo "📋 Check logs: docker-compose logs -f"
fi