# Test script for Windows PowerShell
Write-Host "🧪 Running Tests..." -ForegroundColor Green

Write-Host "`n📦 Rebuilding test containers..." -ForegroundColor Cyan
docker-compose -f docker-compose.test.yml build --no-cache

Write-Host "`n🔬 Running all tests..." -ForegroundColor Cyan
docker-compose -f docker-compose.test.yml up
