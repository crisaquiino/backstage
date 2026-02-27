# Integração de Scripts Python com Backstage.io

Este projeto integra scripts Python de automação do Azure DevOps com Backstage.io usando Docker.

## Estrutura do Projeto

```
Automations/
├── approve_merge_qas.py                    # Script para aprovar e fazer merge de PRs
├── watch_qas_pipelines_notify_teams-internal.py  # Script para monitorar pipelines
├── requirements.txt                        # Dependências Python
├── azure-prs-api/
│   ├── main.py                            # API REST FastAPI
│   ├── Dockerfile                         # Dockerfile da API
│   └── requirements.txt                   # Dependências da API
└── idp/
    ├── Dockerfile                         # Dockerfile do Backstage
    ├── docker-compose.yml                 # Orquestração dos serviços
    └── app-config.production.yaml         # Configuração do Backstage
```

## Pré-requisitos

- Docker e Docker Compose instalados
- Personal Access Token (PAT) do Azure DevOps
- GUID do revisor (REVIEWER_ID)
- (Opcional) Webhook URL do Microsoft Teams

## Configuração

### 1. Variáveis de Ambiente

Crie um arquivo `.env` no diretório `idp/` com as seguintes variáveis:

```env
# Azure DevOps Configuration
AZURE_DEVOPS_PAT=seu_token_aqui
REVIEWER_ID=seu_guid_revisor_aqui

# Microsoft Teams Webhook (opcional)
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/seu_webhook_aqui

# PostgreSQL Configuration
POSTGRES_PASSWORD=sua_senha_segura_aqui
```

### 2. Configuração do Backstage

O Backstage precisa ser configurado separadamente. Se você ainda não tem um projeto Backstage:

1. Crie um novo projeto Backstage:
```bash
npx @backstage/create-app
```

2. Copie os arquivos de configuração para o diretório `idp/`

3. Configure o `app-config.production.yaml` conforme necessário

## Executando Localmente

### Opção 1: Usando Docker Compose (Recomendado)

```bash
cd idp
docker-compose up -d
```

Isso irá iniciar:
- **Backstage** na porta 3000 (frontend) e 7007 (backend)
- **PostgreSQL** na porta 5432
- **API Python** na porta 8000

### Opção 2: Executar apenas a API Python

```bash
cd azure-prs-api
docker build -t azure-prs-api .
docker run -p 8000:8000 \
  -e AZURE_DEVOPS_PAT=seu_token \
  -e REVIEWER_ID=seu_guid \
  azure-prs-api
```

## Endpoints da API

A API REST está disponível em `http://localhost:8000` e oferece os seguintes endpoints:

### Health Check
- `GET /` - Status básico
- `GET /health` - Status detalhado com configurações

### Pull Requests
- `GET /api/v1/prs/active?repo_id={repo_id}` - Lista PRs ativas para branch QAS
- `POST /api/v1/prs/approve-merge` - Aprova e faz merge de PRs

**Exemplo de requisição para aprovar PRs:**
```json
POST /api/v1/prs/approve-merge
{
  "repo_ids": ["ba111f91-8288-4e82-82ce-5c824047c7cb"],
  "pr_ids": [123, 456]
}
```

### Pipelines
- `GET /api/v1/pipelines/status?repo_id={repo_id}` - Status dos pipelines
- `POST /api/v1/pipelines/watch` - Inicia monitoramento (em desenvolvimento)

## Integração com Backstage

Para integrar a API com o Backstage, você pode:

1. **Criar um plugin Backstage** que chame os endpoints da API
2. **Usar a API diretamente** via fetch/axios no frontend do Backstage
3. **Criar um backend plugin** no Backstage que faça proxy para a API Python

### Exemplo de chamada da API no Backstage

```typescript
// No seu plugin Backstage
const response = await fetch('http://azure-prs-api:8000/api/v1/prs/approve-merge', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    repo_ids: ['ba111f91-8288-4e82-82ce-5c824047c7cb']
  })
});
```

## Desenvolvimento

### Executar a API localmente (sem Docker)

```bash
pip install -r requirements.txt
cd azure-prs-api
pip install -r requirements.txt
python main.py
```

### Testar endpoints

```bash
# Health check
curl http://localhost:8000/health

# Listar PRs ativas
curl http://localhost:8000/api/v1/prs/active

# Aprovar PRs
curl -X POST http://localhost:8000/api/v1/prs/approve-merge \
  -H "Content-Type: application/json" \
  -d '{"repo_ids": ["ba111f91-8288-4e82-82ce-5c824047c7cb"]}'
```

## Troubleshooting

### Erro de conexão com Azure DevOps
- Verifique se o PAT está correto e tem as permissões necessárias
- Confirme que o PAT não expirou

### Erro ao importar módulos Python
- Certifique-se de que todos os arquivos Python estão no lugar correto
- Verifique os caminhos no Dockerfile

### Backstage não inicia
- Verifique se você tem um projeto Backstage configurado
- Confirme que o PostgreSQL está rodando e acessível

## Notas

- A API Python expõe os scripts originais como endpoints REST
- O monitoramento de pipelines em background requer implementação adicional (ex: Celery, Redis)
- Para produção, considere adicionar autenticação à API
- Configure CORS adequadamente para produção
