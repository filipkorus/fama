# Test script for Windows PowerShell

# Set console encoding to UTF-8
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[*] Running Tests..." -ForegroundColor Green

Write-Host "`n[*] Rebuilding test containers..." -ForegroundColor Cyan
docker compose -f docker-compose.test.yml build --no-cache

Write-Host "`n[*] Running all tests..." -ForegroundColor Cyan
docker compose -f docker-compose.test.yml up

Write-Host "`n[*] Tests completed." -ForegroundColor Green
docker compose -f docker-compose.test.yml down
