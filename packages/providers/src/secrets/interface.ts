/**
 * Secrets provider interface for encryption/decryption of sensitive data
 * Supports both app-level encryption (libsodium) and AWS KMS
 */

export interface SecretsProvider {
  /**
   * Encrypt plaintext for database storage
   */
  encryptForDb(plaintext: string): Promise<string>;

  /**
   * Decrypt ciphertext from database
   */
  decryptFromDb(ciphertext: string): Promise<string>;

  /**
   * Rotate encryption keys (where supported)
   */
  rotateKey?(): Promise<void>;

  /**
   * Health check
   */
  healthCheck(): Promise<boolean>;
}

export type SecretsProviderType = 'app' | 'kms';

export interface SecretsConfig {
  provider: SecretsProviderType;
  
  // App-level encryption
  secretKey?: string; // Base64 encoded 32-byte key
  keyVersion?: number; // For key rotation support
  
  // AWS KMS
  region?: string;
  keyId?: string;
  accessKeyId?: string;
  secretAccessKey?: string;
}

export interface EncryptedData {
  version: number;
  ciphertext: string;
  nonce?: string; // For libsodium
}

/**
 * Error thrown when decryption fails
 */
export class DecryptionError extends Error {
  constructor(message: string, cause?: Error) {
    super(message);
    this.name = 'DecryptionError';
    if (cause) {
      this.cause = cause;
    }
  }
}