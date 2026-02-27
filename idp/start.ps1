# Script PowerShell para iniciar os serviços no Windows

Write-Host "🚀 Iniciando serviços Backstage.io com integração Azure DevOps..." -ForegroundColor Green

# Verifica se o arquivo .env existe
if (-not (Test-Path .env)) {
    Write-Host "⚠️  Arquivo .env não encontrado!" -ForegroundColor Yellow
    Write-Host "📝 Crie um arquivo .env com as seguintes variáveis:" -ForegroundColor Yellow
    Write-Host "   - AZURE_DEVOPS_PAT" -ForegroundColor Yellow
    Write-Host "   - REVIEWER_ID" -ForegroundColor Yellow
    Write-Host "   - POSTGRES_PASSWORD" -ForegroundColor Yellow
    Write-Host "   - TEAMS_WEBHOOK_URL (opcional)" -ForegroundColor Yellow
    exit 1
}

# Inicia os serviços
docker-compose up -d

Write-Host "✅ Serviços iniciados!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Endpoints disponíveis:" -ForegroundColor Cyan
Write-Host "   - Backstage Frontend: http://localhost:3000"
Write-Host "   - Backstage Backend:  http://localhost:7007"
Write-Host "   - API Python:         http://localhost:8000"
Write-Host "   - API Docs:           http://localhost:8000/docs"
Write-Host ""
Write-Host "📊 Para ver os logs:" -ForegroundColor Cyan
Write-Host "   docker-compose logs -f"
