/**
 * Storage provider factory and exports
 */

import { StorageProvider, StorageConfig, StorageProviderType } from './interface';
import { SupabaseStorageProvider } from './supabase';
import { S3StorageProvider } from './s3';

export * from './interface';
export { SupabaseStorageProvider } from './supabase';
export { S3StorageProvider } from './s3';

/**
 * Create a storage provider instance based on configuration
 */
export function createStorageProvider(config: StorageConfig): StorageProvider {
  switch (config.provider) {
    case 'supabase':
      return new SupabaseStorageProvider(config);
    case 's3':
      return new S3StorageProvider(config);
    default:
      throw new Error(`Unsupported storage provider: ${config.provider}`);
  }
}

/**
 * Create storage provider from environment variables
 */
export function createStorageProviderFromEnv(): StorageProvider {
  const provider = (process.env.STORAGE_PROVIDER as StorageProviderType) || 'supabase';
  
  const config: StorageConfig = {
    provider,
    bucket: process.env.STORAGE_BUCKET || 'exports',
  };

  if (provider === 'supabase') {
    config.supabaseUrl = process.env.SUPABASE_URL;
    config.supabaseKey = process.env.SUPABASE_ANON_KEY;
  } else if (provider === 's3') {
    config.region = process.env.AWS_REGION || 'us-west-2';
    config.accessKeyId = process.env.AWS_ACCESS_KEY_ID;
    config.secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;
    config.endpoint = process.env.S3_ENDPOINT; // For custom S3-compatible endpoints
  }

  return createStorageProvider(config);
}