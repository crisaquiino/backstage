import express from 'express';
import Router from 'express-promise-router';
import { Logger } from 'winston';
import { Config } from '@backstage/config';
import { errorHandler } from '@backstage/backend-common';

// Backstage requer Node.js 18+ que tem fetch nativo
// Se precisar de suporte para versões antigas, use node-fetch

export interface RouterOptions {
  logger: Logger;
  config: Config;
}

/**
 * Cria o router que faz proxy para a API Python de automação do Azure DevOps
 */
export async function createRouter(
  options: RouterOptions,
): Promise<express.Router> {
  const { logger, config } = options;
  const router = Router();

  // URL da API Python - pode ser configurada via app-config.yaml ou variável de ambiente
  const apiUrl =
    config.getOptionalString('azureDevOps.automationApiUrl') ||
    process.env.AZURE_PR_API_URL ||
    'http://azure-prs-api:8000';

  logger.info(`Azure DevOps Automation API URL: ${apiUrl}`);

  // Middleware para log de requisições
  router.use((req, res, next) => {
    logger.debug(`${req.method} ${req.path}`);
    next();
  });

  /**
   * Health check - verifica se a API Python está acessível
   */
  router.get('/health', async (req, res) => {
    try {
      const response = await fetch(`${apiUrl}/health`);
      const data = await response.json();
      res.json({
        status: 'ok',
        pythonApi: data,
      });
    } catch (error: any) {
      logger.error(`Health check failed: ${error.message}`);
      res.status(503).json({
        status: 'error',
        message: 'Python API is not available',
        error: error.message,
      });
    }
  });

  /**
   * Lista PRs ativas para a branch QAS
   * GET /api/azure-devops-automation/prs/active?repo_id={repo_id}
   */
  router.get('/prs/active', async (req, res) => {
    try {
      const repoId = req.query.repo_id as string | undefined;
      const url = repoId
        ? `${apiUrl}/api/v1/prs/active?repo_id=${encodeURIComponent(repoId)}`
        : `${apiUrl}/api/v1/prs/active`;

      logger.info(`Fetching active PRs${repoId ? ` for repo ${repoId}` : ''}`);

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `API returned ${response.status}: ${errorText}`,
        );
      }

      const data = await response.json();
      res.json(data);
    } catch (error: any) {
      logger.error(`Error fetching active PRs: ${error.message}`);
      res.status(500).json({
        error: 'Failed to fetch active PRs',
        message: error.message,
      });
    }
  });

  /**
   * Aprova e faz merge de PRs
   * POST /api/azure-devops-automation/prs/approve-merge
   * Body: { repo_ids?: string[], pr_ids?: number[] }
   */
  router.post('/prs/approve-merge', async (req, res) => {
    try {
      const { repo_ids, pr_ids } = req.body;

      logger.info(
        `Approving and merging PRs: repos=${JSON.stringify(repo_ids)}, prs=${JSON.stringify(pr_ids)}`,
      );

      const response = await fetch(`${apiUrl}/api/v1/prs/approve-merge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repo_ids: repo_ids || undefined,
          pr_ids: pr_ids || undefined,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `API returned ${response.status}: ${errorText}`,
        );
      }

      const data = await response.json();
      logger.info(`PRs processed: ${JSON.stringify(data)}`);
      res.json(data);
    } catch (error: any) {
      logger.error(`Error approving/merging PRs: ${error.message}`);
      res.status(500).json({
        error: 'Failed to approve/merge PRs',
        message: error.message,
      });
    }
  });

  /**
   * Obtém status dos pipelines
   * GET /api/azure-devops-automation/pipelines/status?repo_id={repo_id}
   */
  router.get('/pipelines/status', async (req, res) => {
    try {
      const repoId = req.query.repo_id as string | undefined;
      const url = repoId
        ? `${apiUrl}/api/v1/pipelines/status?repo_id=${encodeURIComponent(repoId)}`
        : `${apiUrl}/api/v1/pipelines/status`;

      logger.info(
        `Fetching pipeline status${repoId ? ` for repo ${repoId}` : ''}`,
      );

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `API returned ${response.status}: ${errorText}`,
        );
      }

      const data = await response.json();
      res.json(data);
    } catch (error: any) {
      logger.error(`Error fetching pipeline status: ${error.message}`);
      res.status(500).json({
        error: 'Failed to fetch pipeline status',
        message: error.message,
      });
    }
  });

  /**
   * Inicia monitoramento de pipelines (em background)
   * POST /api/azure-devops-automation/pipelines/watch
   * Body: { repo_ids?: string[], once?: boolean, timeout_min?: number, poll_sec?: number }
   */
  router.post('/pipelines/watch', async (req, res) => {
    try {
      const { repo_ids, once, timeout_min, poll_sec } = req.body;

      logger.info(
        `Starting pipeline watch: repos=${JSON.stringify(repo_ids)}, once=${once}`,
      );

      const response = await fetch(`${apiUrl}/api/v1/pipelines/watch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repo_ids: repo_ids || undefined,
          once: once || false,
          timeout_min: timeout_min || 60,
          poll_sec: poll_sec || 20,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `API returned ${response.status}: ${errorText}`,
        );
      }

      const data = await response.json();
      res.json(data);
    } catch (error: any) {
      logger.error(`Error starting pipeline watch: ${error.message}`);
      res.status(500).json({
        error: 'Failed to start pipeline watch',
        message: error.message,
      });
    }
  });

  router.use(errorHandler());
  return router;
}
