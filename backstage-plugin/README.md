# Backstage Plugin - Azure DevOps Automation

Backend plugin completo para integração com a API Python de automação do Azure DevOps.

## 📁 Estrutura

```
backstage-plugin/
├── azure-devops-automation-backend/
│   ├── src/
│   │   ├── index.ts              # Exportações principais
│   │   ├── plugin.ts             # Factory do plugin
│   │   ├── types.ts              # Tipos TypeScript
│   │   └── service/
│   │       └── router.ts         # Router com proxy para API Python
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
├── INSTALLATION.md               # Guia de instalação detalhado
└── INTEGRATION_EXAMPLES.md      # Exemplos de integração

```

## 🚀 Instalação Rápida

1. **Copie o plugin para seu projeto Backstage:**
   ```bash
   cp -r backstage-plugin/azure-devops-automation-backend /caminho/do/backstage/plugins/
   ```

2. **Instale as dependências:**
   ```bash
   cd plugins/azure-devops-automation-backend
   yarn install
   ```

3. **Registre no backend** (veja `INSTALLATION.md`)

4. **Configure app-config.yaml:**
   ```yaml
   azureDevOps:
     automationApiUrl: http://azure-prs-api:8000
   ```

## 📡 Endpoints Disponíveis

Todos os endpoints estão disponíveis em `/api/azure-devops-automation/`:

- `GET /health` - Health check
- `GET /prs/active?repo_id={id}` - Lista PRs ativas
- `POST /prs/approve-merge` - Aprova e faz merge de PRs
- `GET /pipelines/status?repo_id={id}` - Status dos pipelines
- `POST /pipelines/watch` - Inicia monitoramento

## 🔧 Uso no Frontend

```typescript
import { useApi } from '@backstage/core-plugin-api';
import { discoveryApiRef } from '@backstage/core-plugin-api';

const MyComponent = () => {
  const discoveryApi = useApi(discoveryApiRef);

  const approvePRs = async () => {
    const baseUrl = await discoveryApi.getBaseUrl('backend');
    const response = await fetch(
      `${baseUrl}/api/azure-devops-automation/prs/approve-merge`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      }
    );
    return await response.json();
  };
};
```

## 📚 Documentação

- **INSTALLATION.md** - Guia completo de instalação
- **INTEGRATION_EXAMPLES.md** - Exemplos de código para diferentes versões do Backstage
- **azure-devops-automation-backend/README.md** - Documentação específica do plugin

## ✅ Funcionalidades

- ✅ Proxy completo para API Python
- ✅ Tratamento de erros
- ✅ Logging integrado
- ✅ Health check
- ✅ Suporte a todos os endpoints da API Python
- ✅ Configuração via app-config.yaml

## 🐛 Troubleshooting

Veja `INSTALLATION.md` para troubleshooting comum.
