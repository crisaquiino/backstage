# Exemplos de Integração no Backend

Este arquivo contém exemplos de como integrar o plugin no backend do Backstage, dependendo da versão e estrutura do seu projeto.

## Exemplo 1: Backstage Moderno (v1.x+)

Para Backstage moderno usando a estrutura padrão com `useHotMemoize`:

```typescript
// packages/backend/src/index.ts

import { createBackend } from '@backstage/backend-defaults';
import azureDevopsAutomation from './plugins/azure-devops-automation-backend';

const backend = createBackend();

// ... outros plugins ...

backend.add(azureDevopsAutomation());

backend.start();
```

## Exemplo 2: Backstage Clássico (v0.x)

Para versões mais antigas do Backstage:

```typescript
// packages/backend/src/index.ts

import { createServiceBuilder } from '@backstage/backend-common';
import { Server } from 'http';
import { Logger } from 'winston';
import { ConfigReader } from '@backstage/config';
import { createRouter } from '@internal/plugin-azure-devops-automation-backend';
import express from 'express';

async function main() {
  const logger = Logger.child({ service: 'backend' });
  const config = ConfigReader.fromConfigs([
    process.env.APP_CONFIG as string,
  ]);

  const database = await createDatabase({ logger, config });

  const service = createServiceBuilder(module)
    .setPort(7007)
    .addRouter('/api', await createApiRouter({ logger, config, database }));

  // Criar router do plugin
  const azureDevopsAutomationRouter = await createRouter({
    logger: logger.child({ plugin: 'azure-devops-automation' }),
    config: config,
  });

  // Adicionar ao serviço
  const app = express();
  app.use('/api/azure-devops-automation', azureDevopsAutomationRouter);
  
  await service.start();
}

main().catch((error) => {
  console.error('Backend failed to start', error);
  process.exit(1);
});
```

## Exemplo 3: Integração Manual com Express

Se você precisa de mais controle:

```typescript
// packages/backend/src/index.ts

import express from 'express';
import { createRouter } from '@internal/plugin-azure-devops-automation-backend';
import { Logger } from 'winston';
import { Config } from '@backstage/config';

async function setupBackend() {
  const app = express();
  const logger = Logger.child({ service: 'backend' });
  const config = /* sua configuração */;

  // ... setup de outros middlewares ...

  // Setup do plugin
  const azureDevopsAutomationRouter = await createRouter({
    logger: logger.child({ plugin: 'azure-devops-automation' }),
    config: config,
  });

  app.use('/api/azure-devops-automation', azureDevopsAutomationRouter);

  // ... resto do setup ...

  return app;
}
```

## Exemplo 4: Com useHotMemoize (Padrão Backstage)

```typescript
// packages/backend/src/index.ts

import { useHotMemoize } from '@backstage/backend-common';
import azureDevopsAutomation from './plugins/azure-devops-automation-backend';

function makeCreateEnv(config: Config) {
  const root = getRootLogger();
  const reader = ConfigReader.fromConfigs(config);
  const discovery = HostDiscovery.fromConfig(reader);

  root.info('Created application config');

  return (plugin: string): PluginEnvironment => {
    const logger = root.child({ type: 'plugin', plugin });
    return { logger, config: reader, discovery };
  };
}

async function main() {
  const config = await loadBackendConfig({ argv, logger });
  const createEnv = makeCreateEnv(config);

  // ... setup de outros serviços ...

  const azureDevopsAutomationEnv = useHotMemoize(module, () => 
    createEnv('azure-devops-automation')
  );

  const azureDevopsAutomationRouter = await azureDevopsAutomation(azureDevopsAutomationEnv);
  
  apiRouter.use('/azure-devops-automation', azureDevopsAutomationRouter);

  // ... resto do código ...
}
```

## Verificação

Após integrar, teste os endpoints:

```bash
# Health check
curl http://localhost:7007/api/azure-devops-automation/health

# Listar PRs ativas
curl http://localhost:7007/api/azure-devops-automation/prs/active

# Aprovar PRs
curl -X POST http://localhost:7007/api/azure-devops-automation/prs/approve-merge \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Notas

- A URL base será `/api/azure-devops-automation`
- Todos os endpoints fazem proxy para a API Python
- O plugin gerencia erros e logging automaticamente
- A configuração vem do `app-config.yaml`
