#!/bin/bash

# MeloTTS Service Startup Script

set -e

echo "🚀 Starting MeloTTS Secure API Service..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating default configuration..."
    cat > .env << EOF
# MeloTTS API Configuration
API_TOKEN=your-secure-api-token-here
PORT=8000
ENABLE_DOCS=true
ALLOWED_ORIGINS=*

# Production settings (uncomment for production)
# ENABLE_DOCS=false
# ALLOWED_ORIGINS=https://yourdomain.com
EOF
    echo "📝 Created .env file. Please edit it with your secure API token!"
    echo "   Current token: your-secure-api-token-here"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it first."
    exit 1
fi

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "❌ Port $port is already in use. Please stop the service using that port first."
        exit 1
    fi
}

# Check if port 8000 is available
check_port 8000

echo "🔧 Building and starting services..."

# Start the service
if [ "$1" = "production" ]; then
    echo "🏭 Starting in PRODUCTION mode with HTTPS..."
    
    # Check if SSL certificates exist
    if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
        echo "⚠️  SSL certificates not found in ssl/ directory."
        echo "   For production, please add your SSL certificates:"
        echo "   - ssl/cert.pem (SSL certificate)"
        echo "   - ssl/key.pem (SSL private key)"
        echo ""
        echo "   Or run in development mode: ./start_service.sh"
        exit 1
    fi
    
    docker-compose --profile production up -d
    echo "✅ Service started with HTTPS on port 443"
    echo "🌐 Access your API at: https://localhost"
else
    echo "🔬 Starting in DEVELOPMENT mode..."
    docker-compose up -d melotts-api
    echo "✅ Service started on port 8000"
    echo "🌐 Access your API at: http://localhost:8000"
fi

echo ""
echo "📋 Service Information:"
echo "   - Health check: curl -H 'Authorization: Bearer your-token' http://localhost:8000/health"
echo "   - API docs: http://localhost:8000/docs"
echo "   - Logs: docker-compose logs -f melotts-api"
echo ""
echo "🛑 To stop the service: docker-compose down"
echo "🔄 To restart: docker-compose restart"
echo ""
echo "🎉 MeloTTS API Service is ready!" 