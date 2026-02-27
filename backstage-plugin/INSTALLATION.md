# Guia de Instalação do Backend Plugin

Este guia explica como instalar e configurar o backend plugin do Azure DevOps Automation no seu projeto Backstage.

## Pré-requisitos

- Projeto Backstage configurado e funcionando
- API Python rodando (via Docker Compose ou separadamente)
- Node.js e Yarn instalados

## Passo a Passo

### 1. Estrutura do Projeto Backstage

Seu projeto Backstage deve ter a seguinte estrutura:

```
backstage/
├── packages/
│   └── backend/
│       └── src/
│           ├── index.ts
│           └── plugins/
├── plugins/
└── app-config.yaml
```

### 2. Copiar o Plugin

Copie a pasta `azure-devops-automation-backend` para `plugins/`:

```bash
# No diretório do seu projeto Backstage
cp -r /caminho/para/Automations/backstage-plugin/azure-devops-automation-backend plugins/
```

### 3. Instalar Dependências

```bash
# No diretório raiz do Backstage
yarn install

# Ou especificamente para o plugin
cd plugins/azure-devops-automation-backend
yarn install
```

### 4. Adicionar ao Workspace

Edite `package.json` na raiz do Backstage para incluir o plugin:

```json
{
  "workspaces": {
    "packages": [
      "packages/*",
      "plugins/*"
    ]
  }
}
```

### 5. Registrar no Backend

Edite `packages/backend/src/index.ts`:

```typescript
import { createServiceBuilder } from '@backstage/backend-common';
import { Server } from 'http';
import { Logger } from 'winston';
import { createRouter } from '@internal/plugin-azure-devops-automation-backend';

// ... outras importações ...

async function main() {
  const config = await loadBackendConfig({ argv, logger });
  const database = await createDatabase({ logger, config });

  // ... código existente ...

  // Importar e configurar o plugin
  const azureDevopsAutomationRouter = await createRouter({
    logger: logger.child({ plugin: 'azure-devops-automation' }),
    config: config,
  });

  // Registrar as rotas
  apiRouter.use('/azure-devops-automation', azureDevopsAutomationRouter);

  // ... resto do código ...
}
```

**Alternativa (usando o padrão do Backstage):**

Se você estiver usando a estrutura padrão do Backstage com `useHotMemoize`:

```typescript
import azureDevopsAutomation from './plugins/azure-devops-automation-backend';

// ... no main() ...

const azureDevopsAutomationEnv = useHotMemoize(module, (backend) => {
  const serviceEnv = useServiceRef(backendServices);
  return {
    logger: backend.logger.child('plugin:azure-devops-automation'),
    config: backend.config,
  };
});

const azureDevopsAutomationRouter = await azureDevopsAutomation(azureDevopsAutomationEnv);
apiRouter.use('/azure-devops-automation', azureDevopsAutomationRouter);
```

### 6. Configurar app-config.yaml

Adicione no `app-config.yaml` ou `app-config.production.yaml`:

```yaml
azureDevOps:
  automationApiUrl: ${AZURE_PR_API_URL}
```

Ou configure diretamente:

```yaml
azureDevOps:
  automationApiUrl: http://azure-prs-api:8000
```

Se estiver usando Docker Compose, a URL será `http://azure-prs-api:8000` (nome do serviço).

### 7. Build e Teste

```bash
# Build do plugin
yarn workspace @internal/plugin-azure-devops-automation-backend build

# Build do backend
yarn workspace backend build

# Iniciar o backend
yarn workspace backend start
```

### 8. Verificar se está funcionando

Teste o endpoint de health check:

```bash
curl http://localhost:7007/api/azure-devops-automation/health
```

Deve retornar algo como:

```json
{
  "status": "ok",
  "pythonApi": {
    "status": "healthy",
    "pat_configured": true,
    "reviewer_id_configured": true
  }
}
```

## Troubleshooting

### Erro: Module not found

Certifique-se de que:
- O plugin está na pasta `plugins/`
- As dependências foram instaladas (`yarn install`)
- O plugin foi adicionado ao workspace

### Erro: Cannot connect to Python API

Verifique:
- A API Python está rodando (`docker ps` ou verifique o processo)
- A URL está correta no `app-config.yaml`
- Se estiver usando Docker, os serviços estão na mesma rede

### Erro: 503 Service Unavailable

A API Python pode não estar acessível. Verifique:
- Logs da API Python: `docker logs azure-prs-api`
- Se a variável `AZURE_PR_API_URL` está configurada corretamente
- Se há firewall bloqueando a conexão

## Próximos Passos

Após instalar o backend plugin, você pode:

1. Criar um frontend plugin que consome esses endpoints
2. Adicionar autenticação/autorização se necessário
3. Criar cards/widgets no Backstage para usar a funcionalidade

Veja `BACKSTAGE_INTEGRATION.md` para exemplos de integração frontend.
