#!/bin/bash

echo "🚀 Starting Backyard Builder Finder..."

# Install dependencies
echo "📦 Installing dependencies..."
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
fi

pnpm install

# Start the web app
echo "🌐 Starting web application..."
cd apps/web
pnpm dev &
WEB_PID=$!

echo "✅ Application starting..."
echo ""
echo "📍 Access the application at:"
echo "   Web App: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $WEB_PID; exit" INT
wait