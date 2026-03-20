#!/bin/bash

# Cleanup Lambda build artifacts after deployment

echo "Cleaning up Lambda build artifacts..."

# Remove Lambda layer build directory
if [ -d "../lambda-layer/python" ]; then
    echo "Removing lambda-layer/python..."
    chmod -R u+w ../lambda-layer/python 2>/dev/null || true
    rm -rf ../lambda-layer/python
fi

# Remove DB Consumer package directory
if [ -d "../ProdDBSystem/Consumer/package" ]; then
    echo "Removing ProdDBSystem/Consumer/package..."
    chmod -R u+w ../ProdDBSystem/Consumer/package 2>/dev/null || true
    rm -rf ../ProdDBSystem/Consumer/package
fi

# Remove Email Consumer package directory
if [ -d "../ProdNotification/Consumer/EmailConsumer/package" ]; then
    echo "Removing ProdNotification/Consumer/EmailConsumer/package..."
    chmod -R u+w ../ProdNotification/Consumer/EmailConsumer/package 2>/dev/null || true
    rm -rf ../ProdNotification/Consumer/EmailConsumer/package
fi

# Remove deployment zips
find .. -name "lambda-deployment.zip" -type f -delete

echo "Cleanup complete!"
