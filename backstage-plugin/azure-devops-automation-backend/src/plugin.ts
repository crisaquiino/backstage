import { createRouter } from './service/router';
import { Router } from 'express';
import { PluginEnvironment } from './types';

export default async function createPlugin(
  env: PluginEnvironment,
): Promise<Router> {
  return await createRouter({
    logger: env.logger,
    config: env.config,
  });
}
