/**
 * AWS KMS secrets provider implementation (stub for future migration)
 */

import { KMS } from 'aws-sdk';
import { SecretsProvider, SecretsConfig, DecryptionError } from './interface';

export class KMSSecretsProvider implements SecretsProvider {
  private kms: KMS;
  private keyId: string;

  constructor(config: SecretsConfig) {
    if (!config.keyId) {
      throw new Error('KMS key ID is required for KMS secrets provider');
    }

    this.kms = new KMS({
      region: config.region || 'us-west-2',
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey
    });

    this.keyId = config.keyId;
  }

  async encryptForDb(plaintext: string): Promise<string> {
    try {
      const result = await this.kms.encrypt({
        KeyId: this.keyId,
        Plaintext: Buffer.from(plaintext, 'utf8')
      }).promise();

      if (!result.CiphertextBlob) {
        throw new Error('KMS encryption returned no ciphertext');
      }

      // Return base64 encoded ciphertext for database storage
      return Buffer.from(result.CiphertextBlob as Uint8Array).toString('base64');
    } catch (error: any) {
      throw new Error(`KMS encryption failed: ${error.message}`);
    }
  }

  async decryptFromDb(ciphertext: string): Promise<string> {
    try {
      // Decode base64 ciphertext
      const ciphertextBlob = Buffer.from(ciphertext, 'base64');

      const result = await this.kms.decrypt({
        CiphertextBlob: ciphertextBlob
      }).promise();

      if (!result.Plaintext) {
        throw new DecryptionError('KMS decryption returned no plaintext');
      }

      return Buffer.from(result.Plaintext as Uint8Array).toString('utf8');
    } catch (error: any) {
      if (error.code === 'InvalidCiphertextException') {
        throw new DecryptionError('Invalid ciphertext - data may be corrupted or key may have changed');
      }
      
      if (error.code === 'AccessDeniedException') {
        throw new DecryptionError('Access denied to KMS key');
      }

      throw new DecryptionError(`KMS decryption failed: ${error.message}`, error);
    }
  }

  async rotateKey(): Promise<void> {
    try {
      await this.kms.scheduleKeyDeletion({
        KeyId: this.keyId,
        PendingWindowInDays: 30 // AWS minimum
      }).promise();

      // Note: This doesn't actually rotate the key in place
      // It schedules deletion. For proper rotation, you'd:
      // 1. Create a new key
      // 2. Re-encrypt all data with the new key
      // 3. Update the key ID configuration
      // 4. Delete the old key
      
      console.warn('KMS key rotation scheduled - implement full rotation logic for production');
    } catch (error: any) {
      throw new Error(`KMS key rotation failed: ${error.message}`);
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      // Try to describe the key to verify access
      await this.kms.describeKey({
        KeyId: this.keyId
      }).promise();

      // Test encryption/decryption with a simple string
      const testString = 'health-check-test';
      const encrypted = await this.encryptForDb(testString);
      const decrypted = await this.decryptFromDb(encrypted);
      
      return decrypted === testString;
    } catch (error) {
      console.error('KMS secrets provider health check failed:', error);
      return false;
    }
  }
}