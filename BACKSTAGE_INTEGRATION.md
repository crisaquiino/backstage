# Guia de Integração com Backstage.io

Este documento explica como integrar a API Python de automação do Azure DevOps com o Backstage.io.

## Opções de Integração

### Opção 1: Backend Plugin (Recomendado)

Crie um backend plugin no Backstage que faça proxy para a API Python.

#### 1. Criar o Plugin

```bash
cd backstage
yarn new --select backend-plugin
# Escolha: azure-devops-automation
```

#### 2. Implementar o Router

Crie `plugins/azure-devops-automation-backend/src/service/router.ts`:

```typescript
import express from 'express';
import Router from 'express-promise-router';
import { Config } from '@backstage/config';
import { errorHandler } from '@backstage/backend-common';

export interface RouterOptions {
  config: Config;
}

export async function createRouter(
  options: RouterOptions,
): Promise<express.Router> {
  const { config } = options;
  const router = Router();

  const apiUrl = config.getString('azureDevOps.automationApiUrl') || 
                 'http://azure-prs-api:8000';

  // Proxy para aprovar PRs
  router.post('/approve-merge', async (req, res) => {
    const response = await fetch(`${apiUrl}/api/v1/prs/approve-merge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body),
    });
    const data = await response.json();
    res.json(data);
  });

  // Proxy para listar PRs ativas
  router.get('/prs/active', async (req, res) => {
    const repoId = req.query.repo_id as string;
    const url = `${apiUrl}/api/v1/prs/active${repoId ? `?repo_id=${repoId}` : ''}`;
    const response = await fetch(url);
    const data = await response.json();
    res.json(data);
  });

  // Proxy para status de pipelines
  router.get('/pipelines/status', async (req, res) => {
    const repoId = req.query.repo_id as string;
    const url = `${apiUrl}/api/v1/pipelines/status${repoId ? `?repo_id=${repoId}` : ''}`;
    const response = await fetch(url);
    const data = await response.json();
    res.json(data);
  });

  router.use(errorHandler());
  return router;
}
```

#### 3. Registrar o Plugin

Em `packages/backend/src/index.ts`:

```typescript
import { azureDevopsAutomationPlugin } from '@backstage/plugin-azure-devops-automation-backend';

// ...

const azureDevopsAutomationRouter = await azureDevopsAutomationPlugin(
  {
    logger,
    config,
  },
);
apiRouter.use('/azure-devops-automation', azureDevopsAutomationRouter);
```

#### 4. Configurar app-config.yaml

```yaml
azureDevOps:
  automationApiUrl: ${AZURE_PR_API_URL}
```

### Opção 2: Frontend Plugin

Crie um frontend plugin que chame diretamente a API Python.

#### 1. Criar o Plugin

```bash
cd backstage
yarn new --select frontend-plugin
# Escolha: azure-devops-automation
```

#### 2. Criar o Componente

```typescript
// plugins/azure-devops-automation/src/components/AutomationCard.tsx
import React, { useState } from 'react';
import { Button, Card, CardContent, CardHeader } from '@material-ui/core';

export const AutomationCard = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleApproveMerge = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/prs/approve-merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader title="Azure DevOps Automation" />
      <CardContent>
        <Button
          variant="contained"
          color="primary"
          onClick={handleApproveMerge}
          disabled={loading}
        >
          {loading ? 'Processando...' : 'Aprovar e Fazer Merge de PRs QAS'}
        </Button>
        {result && (
          <pre>{JSON.stringify(result, null, 2)}</pre>
        )}
      </CardContent>
    </Card>
  );
};
```

### Opção 3: Usar via Backend API (Mais Seguro)

Configure o Backstage para chamar a API Python através do backend, evitando problemas de CORS.

#### 1. Adicionar Proxy no app-config.yaml

```yaml
proxy:
  '/azure-prs-api':
    target: 'http://azure-prs-api:8000'
    changeOrigin: true
    pathRewrite:
      '^/api/proxy/azure-prs-api': ''
```

#### 2. Chamar via Proxy

```typescript
const response = await fetch('/api/proxy/azure-prs-api/api/v1/prs/approve-merge', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({}),
});
```

## Exemplo de Uso Completo

### Card no Backstage para Aprovar PRs

```typescript
import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Button,
  Typography,
  Box,
} from '@material-ui/core';
import { useApi } from '@backstage/core-plugin-api';

export const ApprovePRsCard = () => {
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<any>(null);

  const handleApprove = async () => {
    setLoading(true);
    try {
      // Se usando backend plugin
      const response = await fetch('/api/azure-devops-automation/approve-merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_ids: ['ba111f91-8288-4e82-82ce-5c824047c7cb'],
        }),
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader title="Aprovar PRs QAS" />
      <CardContent>
        <Typography variant="body2" color="textSecondary">
          Aprova e faz merge de todas as PRs ativas para a branch QAS
        </Typography>
        <Box mt={2}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleApprove}
            disabled={loading}
          >
            {loading ? 'Processando...' : 'Executar'}
          </Button>
        </Box>
        {result && (
          <Box mt={2}>
            <Typography variant="body2">
              <pre>{JSON.stringify(result, null, 2)}</pre>
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};
```

## Segurança

- **Nunca exponha a API Python diretamente na internet** sem autenticação
- Use o backend do Backstage como proxy para manter as credenciais seguras
- Configure CORS adequadamente em produção
- Use variáveis de ambiente para credenciais sensíveis

## Troubleshooting

### CORS Errors
- Configure o CORS no `main.py` da API Python para permitir o domínio do Backstage
- Ou use o backend do Backstage como proxy

### Connection Refused
- Verifique se a API Python está rodando: `docker ps`
- Verifique se os serviços estão na mesma rede Docker
- Confirme a URL da API no `app-config.yaml`

### 401 Unauthorized
- Verifique se o PAT está configurado corretamente
- Confirme que o PAT tem as permissões necessárias
