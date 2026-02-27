# Quick Start - Integração Backstage.io

## 🚀 Início Rápido

### 1. Configure as variáveis de ambiente

Crie `idp/.env`:

```env
AZURE_DEVOPS_PAT=seu_token_aqui
REVIEWER_ID=seu_guid_aqui
POSTGRES_PASSWORD=senha_segura
TEAMS_WEBHOOK_URL=https://... (opcional)
```

### 2. Inicie os serviços

**Windows:**
```powershell
cd idp
.\start.ps1
```

**Linux/Mac:**
```bash
cd idp
chmod +x start.sh
./start.sh
```

**Ou manualmente:**
```bash
cd idp
docker-compose up -d
```

### 3. Acesse os serviços

- **Backstage Frontend**: http://localhost:3000
- **Backstage Backend**: http://localhost:7007
- **API Python**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs

## 📝 Testar a API

### Listar PRs ativas
```bash
curl http://localhost:8000/api/v1/prs/active
```

### Aprovar e fazer merge de PRs
```bash
curl -X POST http://localhost:8000/api/v1/prs/approve-merge \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Ver status de pipelines
```bash
curl http://localhost:8000/api/v1/pipelines/status
```

## 🔧 Próximos Passos

1. Configure o Backstage (veja `BACKSTAGE_INTEGRATION.md`)
2. Crie plugins para integrar com a UI
3. Configure autenticação se necessário

## 📚 Documentação Completa

- `README.md` - Documentação completa
- `BACKSTAGE_INTEGRATION.md` - Guia de integração com Backstage
