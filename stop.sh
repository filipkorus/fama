#!/bin/bash
# Stop script for Linux/Mac

echo "[*] Stopping Post-Quantum Cryptography Project..."

docker-compose down

echo ""
echo "[+] Application stopped successfully!"
echo "[i] To remove all data (including database), run: docker-compose down -v"
