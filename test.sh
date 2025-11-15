#!/bin/bash
# Test script for Linux/Mac

echo "[*] Running Tests..."

echo ""
echo "[*] Rebuilding test containers..."
docker-compose -f docker-compose.test.yml build --no-cache

echo ""
echo "[*] Running all tests..."
docker-compose -f docker-compose.test.yml up

echo ""
echo "[*] Tests completed."
docker-compose -f docker-compose.test.yml down
