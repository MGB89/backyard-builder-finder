/**
 * Main provider package exports
 */

// Storage providers
export * from './storage';

// Queue providers  
export * from './queue';

// Secrets providers
export * from './secrets';

// Metrics providers
export * from './metrics';

// Geocoding providers (to be implemented)
export * from './geocode';

/**
 * Provider status interface for monitoring which providers are active
 */
export interface ProviderStatus {
  storage: {
    provider: string;
    healthy: boolean;
    error?: string;
  };
  queue: {
    provider: string;
    healthy: boolean;
    error?: string;
  };
  secrets: {
    provider: string;
    healthy: boolean;
    error?: string;
  };
  metrics: {
    provider: string;
    healthy: boolean;
    error?: string;
  };
}

/**
 * Get status of all configured providers
 */
export async function getProviderStatus(): Promise<ProviderStatus> {
  const results: Partial<ProviderStatus> = {};

  try {
    const { createStorageProviderFromEnv } = await import('./storage');
    const storageProvider = createStorageProviderFromEnv();
    results.storage = {
      provider: process.env.STORAGE_PROVIDER || 'supabase',
      healthy: await storageProvider.healthCheck()
    };
  } catch (error: any) {
    results.storage = {
      provider: process.env.STORAGE_PROVIDER || 'supabase',
      healthy: false,
      error: error.message
    };
  }

  try {
    const { createQueueProviderFromEnv } = await import('./queue');
    const queueProvider = createQueueProviderFromEnv();
    results.queue = {
      provider: process.env.QUEUE_PROVIDER || 'pgboss',
      healthy: await queueProvider.healthCheck()
    };
  } catch (error: any) {
    results.queue = {
      provider: process.env.QUEUE_PROVIDER || 'pgboss',
      healthy: false,
      error: error.message
    };
  }

  try {
    const { createSecretsProviderFromEnv } = await import('./secrets');
    const secretsProvider = createSecretsProviderFromEnv();
    results.secrets = {
      provider: process.env.SECRETS_PROVIDER || 'app',
      healthy: await secretsProvider.healthCheck()
    };
  } catch (error: any) {
    results.secrets = {
      provider: process.env.SECRETS_PROVIDER || 'app',
      healthy: false,
      error: error.message
    };
  }

  try {
    const { createMetricsProviderFromEnv } = await import('./metrics');
    const metricsProvider = createMetricsProviderFromEnv();
    results.metrics = {
      provider: process.env.METRICS_PROVIDER || 'otel',
      healthy: await metricsProvider.healthCheck()
    };
  } catch (error: any) {
    results.metrics = {
      provider: process.env.METRICS_PROVIDER || 'otel',
      healthy: false,
      error: error.message
    };
  }

  return results as ProviderStatus;
}