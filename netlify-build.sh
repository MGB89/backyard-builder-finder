#!/bin/bash
# Netlify build script that only builds the web app

echo "Building Next.js app only..."
cd apps/web
npm install
npm run build
echo "Build complete!"