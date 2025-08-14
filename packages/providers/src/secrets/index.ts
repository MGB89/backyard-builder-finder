/**
 * Secrets provider factory and exports
 */

import { SecretsProvider, SecretsConfig, SecretsProviderType } from './interface';
import { AppSecretsProvider } from './app';
import { KMSSecretsProvider } from './kms';

export * from './interface';
export { AppSecretsProvider } from './app';
export { KMSSecretsProvider } from './kms';

/**
 * Create a secrets provider instance based on configuration
 */
export function createSecretsProvider(config: SecretsConfig): SecretsProvider {
  switch (config.provider) {
    case 'app':
      return new AppSecretsProvider(config);
    case 'kms':
      return new KMSSecretsProvider(config);
    default:
      throw new Error(`Unsupported secrets provider: ${config.provider}`);
  }
}

/**
 * Create secrets provider from environment variables
 */
export function createSecretsProviderFromEnv(): SecretsProvider {
  const provider = (process.env.SECRETS_PROVIDER as SecretsProviderType) || 'app';
  
  const config: SecretsConfig = {
    provider
  };

  if (provider === 'app') {
    config.secretKey = process.env.ENCRYPTION_SECRET_KEY;
    config.keyVersion = parseInt(process.env.ENCRYPTION_KEY_VERSION || '1');
    
    if (!config.secretKey) {
      throw new Error('ENCRYPTION_SECRET_KEY environment variable is required for app secrets provider');
    }
  } else if (provider === 'kms') {
    config.region = process.env.AWS_REGION || 'us-west-2';
    config.keyId = process.env.KMS_KEY_ID;
    config.accessKeyId = process.env.AWS_ACCESS_KEY_ID;
    config.secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;
    
    if (!config.keyId) {
      throw new Error('KMS_KEY_ID environment variable is required for KMS secrets provider');
    }
  }

  return createSecretsProvider(config);
}