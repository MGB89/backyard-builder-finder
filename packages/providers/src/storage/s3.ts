/**
 * AWS S3 Storage provider implementation (stub for future migration)
 */

import { S3 } from 'aws-sdk';
import { StorageProvider, StorageMetadata, UploadOptions, SignedUrlOptions, StorageConfig } from './interface';

export class S3StorageProvider implements StorageProvider {
  private s3: S3;
  private bucketName: string;

  constructor(config: StorageConfig) {
    if (!config.region) {
      throw new Error('AWS region is required for S3 provider');
    }

    this.s3 = new S3({
      region: config.region,
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey,
      endpoint: config.endpoint,
      s3ForcePathStyle: !!config.endpoint // Required for custom endpoints
    });
    
    this.bucketName = config.bucket;
  }

  async putObject(
    key: string,
    data: Buffer | ReadableStream | Uint8Array,
    options?: UploadOptions
  ): Promise<void> {
    // Convert ReadableStream to Buffer if needed
    let bodyData: Buffer | Uint8Array;
    if (data instanceof ReadableStream) {
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
      
      bodyData = Buffer.concat(chunks);
    } else {
      bodyData = data;
    }

    const params: S3.PutObjectRequest = {
      Bucket: this.bucketName,
      Key: key,
      Body: bodyData,
      ContentType: options?.contentType,
      Metadata: options?.metadata
    };

    if (options?.ttl) {
      const expiresDate = new Date();
      expiresDate.setSeconds(expiresDate.getSeconds() + options.ttl);
      params.Expires = expiresDate;
    }

    await this.s3.putObject(params).promise();
  }

  async getSignedUrl(key: string, options?: SignedUrlOptions): Promise<string> {
    const operation = options?.download ? 'getObject' : 'getObject';
    const expires = options?.expiresIn || 3600;

    const params = {
      Bucket: this.bucketName,
      Key: key,
      Expires: expires
    };

    return this.s3.getSignedUrl(operation, params);
  }

  async head(key: string): Promise<StorageMetadata | null> {
    try {
      const result = await this.s3.headObject({
        Bucket: this.bucketName,
        Key: key
      }).promise();

      return {
        contentType: result.ContentType,
        size: result.ContentLength,
        lastModified: result.LastModified,
        etag: result.ETag?.replace(/"/g, '') // Remove quotes from ETag
      };
    } catch (error: any) {
      if (error.statusCode === 404) {
        return null;
      }
      throw error;
    }
  }

  async delete(key: string): Promise<void> {
    await this.s3.deleteObject({
      Bucket: this.bucketName,
      Key: key
    }).promise();
  }

  async deleteMany(keys: string[]): Promise<void> {
    if (keys.length === 0) return;

    await this.s3.deleteObjects({
      Bucket: this.bucketName,
      Delete: {
        Objects: keys.map(key => ({ Key: key }))
      }
    }).promise();
  }

  async list(prefix?: string, limit?: number): Promise<string[]> {
    const params: S3.ListObjectsV2Request = {
      Bucket: this.bucketName,
      Prefix: prefix,
      MaxKeys: limit
    };

    const result = await this.s3.listObjectsV2(params).promise();
    return result.Contents?.map(obj => obj.Key || '') || [];
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.s3.headBucket({ Bucket: this.bucketName }).promise();
      return true;
    } catch (error) {
      console.error('S3 health check failed:', error);
      return false;
    }
  }
}