#!/bin/bash
# Netlify build script that only builds the web app

echo "Building Next.js app only..."
cd apps/web
pnpm install --frozen-lockfile
pnpm build
echo "Build complete!"