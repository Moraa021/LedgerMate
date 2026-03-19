#!/bin/bash

echo "🚀 Building LedgerMate for Vercel..."

# Install dependencies
pip install -r requirements.txt

# Create instance directory if it doesn't exist
mkdir -p instance

# Set up production database (if using PostgreSQL)
if [ "$VERCEL_ENV" == "production" ]; then
    echo "Setting up production database..."
    # Any production-specific setup
fi

echo "✅ Build complete!"