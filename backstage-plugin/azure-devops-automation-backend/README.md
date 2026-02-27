# Azure DevOps Automation Backend Plugin

Backend plugin do Backstage que faz proxy para a API Python de automação do Azure DevOps.

## Instalação

### 1. Copiar o plugin para o projeto Backstage

Copie a pasta `azure-devops-automation-backend` para o diretório `plugins/` do seu projeto Backstage:

```bash
cp -r backstage-plugin/azure-devops-automation-backend /caminho/do/backstage/plugins/
```

### 2. Instalar dependências

No diretório do plugin:

```bash
cd plugins/azure-devops-automation-backend
yarn install
```

### 3. Registrar o plugin no backend

Edite `packages/backend/src/index.ts`:

```typescript
import azureDevopsAutomation from './plugins/azure-devops-automation-backend';

// ...

async function main() {
  // ... código existente ...

  const azureDevopsAutomationEnv = useHotMemoize(module, (backend) => {
    const serviceEnv = useServiceRef(backendServices);
    return {
      logger: backend.logger.child('plugin:azure-devops-automation'),
      config: backend.config,
    };
  });

  const azureDevopsAutomationRouter = await azureDevopsAutomation(azureDevopsAutomationEnv);
  apiRouter.use('/azure-devops-automation', azureDevopsAutomationRouter);

  // ... resto do código ...
}
```

### 4. Configurar app-config.yaml

Adicione a configuração no `app-config.yaml` ou `app-config.production.yaml`:

```yaml
azureDevOps:
  automationApiUrl: ${AZURE_PR_API_URL}
```

Ou configure diretamente:

```yaml
azureDevOps:
  automationApiUrl: http://azure-prs-api:8000
```

### 5. Build e start

```bash
# Build do plugin
yarn workspace @internal/plugin-azure-devops-automation-backend build

# Build do backend
yarn workspace backend build

# Start
yarn workspace backend start
```

## Endpoints

O plugin expõe os seguintes endpoints no backend do Backstage:

### Health Check
- `GET /api/azure-devops-automation/health` - Verifica se a API Python está acessível

### Pull Requests
- `GET /api/azure-devops-automation/prs/active?repo_id={repo_id}` - Lista PRs ativas
- `POST /api/azure-devops-automation/prs/approve-merge` - Aprova e faz merge de PRs

### Pipelines
- `GET /api/azure-devops-automation/pipelines/status?repo_id={repo_id}` - Status dos pipelines
- `POST /api/azure-devops-automation/pipelines/watch` - Inicia monitoramento

## Uso no Frontend

Exemplo de como chamar os endpoints do frontend:

```typescript
import { useApi } from '@backstage/core-plugin-api';
import { discoveryApiRef } from '@backstage/core-plugin-api';

export const MyComponent = () => {
  const discoveryApi = useApi(discoveryApiRef);

  const approvePRs = async () => {
    const baseUrl = await discoveryApi.getBaseUrl('backend');
    const response = await fetch(`${baseUrl}/api/azure-devops-automation/prs/approve-merge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await response.json();
    return data;
  };

  // ...
};
```

## Desenvolvimento

```bash
# Desenvolvimento com hot reload
yarn workspace @internal/plugin-azure-devops-automation-backend start

# Build
yarn workspace @internal/plugin-azure-devops-automation-backend build

# Testes
yarn workspace @internal/plugin-azure-devops-automation-backend test
```
