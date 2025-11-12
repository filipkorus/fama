# Start Development Environment
# Uruchamia tylko baze danych dla lokalnego developmentu

# Set console encoding to UTF-8
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[*] Starting PostgreSQL for local development..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "[!] .env file not found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "[+] .env file created." -ForegroundColor Green
}

Write-Host "`n[*] Starting database container..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml up -d

Write-Host "`n[+] Database started successfully!" -ForegroundColor Green
Write-Host "`n[i] Connection details:" -ForegroundColor Cyan
Write-Host "  Host: localhost" -ForegroundColor White
Write-Host "  Port: 5432" -ForegroundColor White
Write-Host "  Database: cryptography_db" -ForegroundColor White
Write-Host "  Username: postgres" -ForegroundColor White
Write-Host "  Password: postgres" -ForegroundColor White

Write-Host "`n[>] Next steps:" -ForegroundColor Yellow
Write-Host "  1. Backend: cd backend && venv\Scripts\activate && python app.py" -ForegroundColor White
Write-Host "  2. Frontend: cd frontend && npm run dev" -ForegroundColor White
