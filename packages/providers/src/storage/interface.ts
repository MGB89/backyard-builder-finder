/**
 * Storage provider interface for file storage operations
 * Supports both Supabase Storage and AWS S3 backends
 */

export interface StorageMetadata {
  contentType?: string;
  size?: number;
  lastModified?: Date;
  etag?: string;
  [key: string]: any;
}

export interface UploadOptions {
  contentType?: string;
  ttl?: number; // Time to live in seconds
  metadata?: Record<string, string>;
}

export interface SignedUrlOptions {
  expiresIn?: number; // Expiration in seconds
  download?: boolean; // Force download vs inline
}

export interface StorageProvider {
  /**
   * Upload a file from stream or buffer
   */
  putObject(
    key: string,
    data: Buffer | ReadableStream | Uint8Array,
    options?: UploadOptions
  ): Promise<void>;

  /**
   * Generate a signed URL for accessing an object
   */
  getSignedUrl(key: string, options?: SignedUrlOptions): Promise<string>;

  /**
   * Get object metadata without downloading
   */
  head(key: string): Promise<StorageMetadata | null>;

  /**
   * Delete an object
   */
  delete(key: string): Promise<void>;

  /**
   * Delete multiple objects
   */
  deleteMany(keys: string[]): Promise<void>;

  /**
   * List objects with prefix
   */
  list(prefix?: string, limit?: number): Promise<string[]>;

  /**
   * Check if provider is healthy
   */
  healthCheck(): Promise<boolean>;
}

export type StorageProviderType = 'supabase' | 's3';

export interface StorageConfig {
  provider: StorageProviderType;
  bucket: string;
  
  // Supabase specific
  supabaseUrl?: string;
  supabaseKey?: string;
  
  // AWS S3 specific
  region?: string;
  accessKeyId?: string;
  secretAccessKey?: string;
  endpoint?: string; // For S3-compatible services
}