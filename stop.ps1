# Stop script for Windows PowerShell

# Set console encoding to UTF-8
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[*] Stopping Post-Quantum Cryptography Project..." -ForegroundColor Yellow

docker compose down

Write-Host "`n[+] Application stopped successfully!" -ForegroundColor Green
Write-Host "[i] To remove all data (including database), run: docker compose down -v" -ForegroundColor Cyan
