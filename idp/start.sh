#!/bin/bash
# Script para iniciar os serviços

echo "🚀 Iniciando serviços Backstage.io com integração Azure DevOps..."

# Verifica se o arquivo .env existe
if [ ! -f .env ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "📝 Crie um arquivo .env com as seguintes variáveis:"
    echo "   - AZURE_DEVOPS_PAT"
    echo "   - REVIEWER_ID"
    echo "   - POSTGRES_PASSWORD"
    echo "   - TEAMS_WEBHOOK_URL (opcional)"
    exit 1
fi

# Inicia os serviços
docker-compose up -d

echo "✅ Serviços iniciados!"
echo ""
echo "📍 Endpoints disponíveis:"
echo "   - Backstage Frontend: http://localhost:3000"
echo "   - Backstage Backend:  http://localhost:7007"
echo "   - API Python:         http://localhost:8000"
echo "   - API Docs:           http://localhost:8000/docs"
echo ""
echo "📊 Para ver os logs:"
echo "   docker-compose logs -f"
