#!/bin/bash
# Start script for Linux/Mac

echo "[*] Starting Post-Quantum Cryptography Project..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "[!] .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "[+] .env file created. Please review and update if needed."
fi

echo ""
echo "[*] Starting Docker containers..."
docker compose up --build

echo ""
echo "[+] Application started successfully!"
echo "[>] Access the application at: http://localhost:8080"
