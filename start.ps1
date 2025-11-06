# Start script for Windows PowerShell
Write-Host "🚀 Starting Post-Quantum Cryptography Project..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "⚠️  .env file not found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✅ .env file created. Please review and update if needed." -ForegroundColor Green
}

Write-Host "`n🐳 Starting Docker containers..." -ForegroundColor Cyan
docker-compose up --build

Write-Host "`n✅ Application started successfully!" -ForegroundColor Green
Write-Host "🌐 Access the application at: http://localhost:8080" -ForegroundColor Cyan
