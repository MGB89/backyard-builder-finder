/**
 * App-level secrets provider using libsodium (NaCl) for encryption
 */

import * as sodium from 'libsodium-wrappers';
import { SecretsProvider, SecretsConfig, EncryptedData, DecryptionError } from './interface';

export class AppSecretsProvider implements SecretsProvider {
  private secretKey: Uint8Array;
  private keyVersion: number;
  private isReady = false;

  constructor(config: SecretsConfig) {
    if (!config.secretKey) {
      throw new Error('Secret key is required for app secrets provider');
    }

    this.keyVersion = config.keyVersion || 1;
    
    try {
      // Decode base64 secret key
      this.secretKey = sodium.from_base64(config.secretKey, sodium.base64_variants.ORIGINAL);
      
      if (this.secretKey.length !== 32) {
        throw new Error('Secret key must be 32 bytes when decoded from base64');
      }
    } catch (error) {
      throw new Error(`Invalid secret key format: ${error}`);
    }
  }

  private async ensureReady(): Promise<void> {
    if (!this.isReady) {
      await sodium.ready;
      this.isReady = true;
    }
  }

  async encryptForDb(plaintext: string): Promise<string> {
    await this.ensureReady();

    try {
      // Generate a random nonce for this encryption
      const nonce = sodium.randombytes_buf(sodium.crypto_secretbox_NONCEBYTES);
      
      // Encrypt the plaintext
      const ciphertext = sodium.crypto_secretbox_easy(plaintext, nonce, this.secretKey);
      
      // Create the encrypted data structure
      const encryptedData: EncryptedData = {
        version: this.keyVersion,
        ciphertext: sodium.to_base64(ciphertext, sodium.base64_variants.ORIGINAL),
        nonce: sodium.to_base64(nonce, sodium.base64_variants.ORIGINAL)
      };

      // Return as JSON string for database storage
      return JSON.stringify(encryptedData);
    } catch (error: any) {
      throw new Error(`Encryption failed: ${error.message}`);
    }
  }

  async decryptFromDb(ciphertext: string): Promise<string> {
    await this.ensureReady();

    try {
      // Parse the encrypted data structure
      let encryptedData: EncryptedData;
      try {
        encryptedData = JSON.parse(ciphertext);
      } catch (error) {
        throw new DecryptionError('Invalid encrypted data format');
      }

      // Validate the structure
      if (!encryptedData.ciphertext || !encryptedData.nonce || !encryptedData.version) {
        throw new DecryptionError('Missing required fields in encrypted data');
      }

      // Check version compatibility
      if (encryptedData.version > this.keyVersion) {
        throw new DecryptionError(`Encrypted data version ${encryptedData.version} is newer than current key version ${this.keyVersion}`);
      }

      // Decode the base64 data
      const ciphertextBytes = sodium.from_base64(encryptedData.ciphertext, sodium.base64_variants.ORIGINAL);
      const nonceBytes = sodium.from_base64(encryptedData.nonce, sodium.base64_variants.ORIGINAL);

      // Decrypt the data
      const plaintext = sodium.crypto_secretbox_open_easy(ciphertextBytes, nonceBytes, this.secretKey);
      
      // Convert to string
      return sodium.to_string(plaintext);
    } catch (error: any) {
      if (error instanceof DecryptionError) {
        throw error;
      }
      throw new DecryptionError(`Decryption failed: ${error.message}`, error);
    }
  }

  async rotateKey(): Promise<void> {
    // Key rotation would require:
    // 1. Generate new key
    // 2. Update keyVersion
    // 3. Re-encrypt all existing data with new key
    // 4. Update configuration
    
    throw new Error('Key rotation not implemented - requires coordinated data migration');
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.ensureReady();
      
      // Test encryption/decryption with a simple string
      const testString = 'health-check-test';
      const encrypted = await this.encryptForDb(testString);
      const decrypted = await this.decryptFromDb(encrypted);
      
      return decrypted === testString;
    } catch (error) {
      console.error('App secrets provider health check failed:', error);
      return false;
    }
  }

  /**
   * Generate a new random secret key (for initial setup)
   */
  static async generateSecretKey(): Promise<string> {
    await sodium.ready;
    const key = sodium.randombytes_buf(32);
    return sodium.to_base64(key, sodium.base64_variants.ORIGINAL);
  }

  /**
   * Validate a secret key format
   */
  static validateSecretKey(secretKey: string): boolean {
    try {
      const decoded = sodium.from_base64(secretKey, sodium.base64_variants.ORIGINAL);
      return decoded.length === 32;
    } catch (error) {
      return false;
    }
  }
}