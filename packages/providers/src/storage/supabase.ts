/**
 * Supabase Storage provider implementation
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { StorageProvider, StorageMetadata, UploadOptions, SignedUrlOptions, StorageConfig } from './interface';

export class SupabaseStorageProvider implements StorageProvider {
  private client: SupabaseClient;
  private bucketName: string;

  constructor(config: StorageConfig) {
    if (!config.supabaseUrl || !config.supabaseKey) {
      throw new Error('Supabase URL and key are required');
    }

    this.client = createClient(config.supabaseUrl, config.supabaseKey);
    this.bucketName = config.bucket;
  }

  async putObject(
    key: string,
    data: Buffer | ReadableStream | Uint8Array,
    options?: UploadOptions
  ): Promise<void> {
    const uploadOptions: any = {};
    
    if (options?.contentType) {
      uploadOptions.contentType = options.contentType;
    }
    
    if (options?.metadata) {
      uploadOptions.metadata = options.metadata;
    }

    // Convert data to appropriate format for Supabase
    let uploadData: Buffer | File;
    if (data instanceof ReadableStream) {
      // Convert ReadableStream to Buffer
      const chunks: Uint8Array[] = [];
      const reader = data.getReader();
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(value);
        }
      } finally {
        reader.releaseLock();
      }
      
      uploadData = Buffer.concat(chunks);
    } else {
      uploadData = data instanceof Uint8Array ? Buffer.from(data) : data;
    }

    const { error } = await this.client.storage
      .from(this.bucketName)
      .upload(key, uploadData, {
        ...uploadOptions,
        upsert: true // Allow overwriting existing files
      });

    if (error) {
      throw new Error(`Failed to upload to Supabase Storage: ${error.message}`);
    }
  }

  async getSignedUrl(key: string, options?: SignedUrlOptions): Promise<string> {
    const expiresIn = options?.expiresIn || 3600; // Default 1 hour
    
    const { data, error } = await this.client.storage
      .from(this.bucketName)
      .createSignedUrl(key, expiresIn, {
        download: options?.download || false
      });

    if (error) {
      throw new Error(`Failed to create signed URL: ${error.message}`);
    }

    if (!data?.signedUrl) {
      throw new Error('No signed URL returned from Supabase');
    }

    return data.signedUrl;
  }

  async head(key: string): Promise<StorageMetadata | null> {
    const { data, error } = await this.client.storage
      .from(this.bucketName)
      .list('', {
        search: key
      });

    if (error) {
      throw new Error(`Failed to get object metadata: ${error.message}`);
    }

    const file = data?.find(f => f.name === key);
    if (!file) {
      return null;
    }

    return {
      contentType: file.metadata?.mimetype,
      size: file.metadata?.size,
      lastModified: file.updated_at ? new Date(file.updated_at) : undefined,
      etag: file.metadata?.eTag
    };
  }

  async delete(key: string): Promise<void> {
    const { error } = await this.client.storage
      .from(this.bucketName)
      .remove([key]);

    if (error) {
      throw new Error(`Failed to delete object: ${error.message}`);
    }
  }

  async deleteMany(keys: string[]): Promise<void> {
    const { error } = await this.client.storage
      .from(this.bucketName)
      .remove(keys);

    if (error) {
      throw new Error(`Failed to delete objects: ${error.message}`);
    }
  }

  async list(prefix?: string, limit?: number): Promise<string[]> {
    const { data, error } = await this.client.storage
      .from(this.bucketName)
      .list(prefix || '', {
        limit: limit || 1000
      });

    if (error) {
      throw new Error(`Failed to list objects: ${error.message}`);
    }

    return data?.map(file => file.name) || [];
  }

  async healthCheck(): Promise<boolean> {
    try {
      // Try to list the bucket to verify access
      await this.client.storage.from(this.bucketName).list('', { limit: 1 });
      return true;
    } catch (error) {
      console.error('Supabase Storage health check failed:', error);
      return false;
    }
  }
}