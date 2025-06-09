#!/bin/bash

echo "🔨 Building Docker containers..."
docker-compose build --no-cache

echo "🚀 Starting services..."
docker-compose up -d

echo "📋 Checking service status..."
docker-compose ps

echo "📝 Backend logs (last 50 lines):"
docker-compose logs --tail=50 backend

echo "✅ Services are running!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"