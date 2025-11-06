# Stop script for Windows PowerShell
Write-Host "🛑 Stopping Post-Quantum Cryptography Project..." -ForegroundColor Yellow

docker-compose down

Write-Host "`n✅ Application stopped successfully!" -ForegroundColor Green
Write-Host "💡 To remove all data (including database), run: docker-compose down -v" -ForegroundColor Cyan
