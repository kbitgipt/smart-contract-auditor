#!/bin/bash

echo "🧹 Stopping and removing containers..."
docker-compose down

echo "🗑️ Removing unused images..."
docker image prune -f

echo "📦 Removing unused volumes..."
docker volume prune -f

echo "✅ Cleanup completed!"