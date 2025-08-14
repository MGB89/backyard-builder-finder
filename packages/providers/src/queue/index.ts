/**
 * Queue provider factory and exports
 */

import { QueueProvider, QueueConfig, QueueProviderType } from './interface';
import { PgBossQueueProvider } from './pgboss';
import { SQSQueueProvider } from './sqs';

export * from './interface';
export { PgBossQueueProvider } from './pgboss';
export { SQSQueueProvider } from './sqs';

/**
 * Create a queue provider instance based on configuration
 */
export function createQueueProvider(config: QueueConfig): QueueProvider {
  switch (config.provider) {
    case 'pgboss':
      return new PgBossQueueProvider(config);
    case 'sqs':
      return new SQSQueueProvider(config);
    default:
      throw new Error(`Unsupported queue provider: ${config.provider}`);
  }
}

/**
 * Create queue provider from environment variables
 */
export function createQueueProviderFromEnv(): QueueProvider {
  const provider = (process.env.QUEUE_PROVIDER as QueueProviderType) || 'pgboss';
  
  const config: QueueConfig = {
    provider
  };

  if (provider === 'pgboss') {
    config.connectionString = process.env.DATABASE_URL;
  } else if (provider === 'sqs') {
    config.region = process.env.AWS_REGION || 'us-west-2';
    config.accessKeyId = process.env.AWS_ACCESS_KEY_ID;
    config.secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;
    config.queueUrlPrefix = process.env.SQS_QUEUE_URL_PREFIX;
  }

  return createQueueProvider(config);
}