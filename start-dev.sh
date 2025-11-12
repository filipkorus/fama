#!/bin/bash
# Start Development Environment
# Uruchamia tylko baze danych dla lokalnego developmentu

echo "[*] Starting PostgreSQL for local development..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "[!] .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "[+] .env file created."
fi

echo ""
echo "[*] Starting database container..."
docker-compose -f docker-compose.dev.yml up -d

echo ""
echo "[+] Database started successfully!"
echo ""
echo "[i] Connection details:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: cryptography_db"
echo "  Username: postgres"
echo "  Password: postgres"

echo ""
echo "[>] Next steps:"
echo "  1. Backend: cd backend && source venv/bin/activate && python app.py"
echo "  2. Frontend: cd frontend && npm run dev"
