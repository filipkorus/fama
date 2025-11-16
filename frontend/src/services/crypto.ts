/**
 * Cryptographic utilities for ML-KEM (Kyber768) key generation
 * Uses the mlkem library for post-quantum cryptographic key generation
 */

import { MlKem768 } from 'mlkem';

/**
 * Generate ML-KEM (Kyber768) keypair using mlkem library
 * 
 * @returns Promise<{publicKey: string, privateKey: string}>
 *   - publicKey: Base64-encoded public key
 *   - privateKey: Base64-encoded private key
 * 
 * @throws Error if key generation fails
 */
export async function generateMLKEMKeypair(): Promise<{
  publicKey: string;
  privateKey: string;
}> {
  try {
    console.log('Generating ML-KEM (Kyber768) keypair...');
    
    // Create ML-KEM768 instance
    const mlkem = new MlKem768();
    
    // Generate keypair - returns Promise<[publicKey: Uint8Array, privateKey: Uint8Array]>
    const [publicKeyBytes, privateKeyBytes] = await mlkem.generateKeyPair();
    
    console.log('Keys generated:', {
      publicKeyBytesLength: publicKeyBytes.length,
      privateKeyBytesLength: privateKeyBytes.length,
      publicKeyBytesType: publicKeyBytes.constructor.name,
    });
    
    // Convert to Base64 for storage and transmission
    const publicKeyBase64 = toBase64(publicKeyBytes);
    const privateKeyBase64 = toBase64(privateKeyBytes);
    
    console.log('ML-KEM (Kyber768) keypair generated successfully');
    console.log(`Public key size: ${publicKeyBytes.length} bytes (${publicKeyBase64.length} Base64 chars)`);
    console.log(`Private key size: ${privateKeyBytes.length} bytes (${privateKeyBase64.length} Base64 chars)`);
    console.log('Returning keys as strings:', {
      publicKeyType: typeof publicKeyBase64,
      privateKeyType: typeof privateKeyBase64,
      publicKeyLength: publicKeyBase64.length,
      privateKeyLength: privateKeyBase64.length,
    });
    
    return {
      publicKey: publicKeyBase64,
      privateKey: privateKeyBase64,
    };
  } catch (error) {
    console.error('Failed to generate ML-KEM keypair:', error);
    throw new Error('Failed to generate cryptographic keys');
  }
}

/**
 * Convert Uint8Array to Base64 string
 */
function toBase64(buffer: Uint8Array): string {
  try {
    // Using the modern approach with btoa and String.fromCharCode
    let binary = '';
    const chunkSize = 0x8000; // Process in chunks to avoid stack overflow
    
    for (let i = 0; i < buffer.length; i += chunkSize) {
      const chunk = buffer.subarray(i, i + chunkSize);
      binary += String.fromCharCode.apply(null, Array.from(chunk) as any);
    }
    
    const base64 = btoa(binary);
    console.log(`Base64 encoding: ${buffer.length} bytes → ${base64.length} chars`);
    return base64;
  } catch (error) {
    console.error('Base64 encoding failed:', error);
    throw new Error(`Failed to encode keys to Base64: ${error}`);
  }
}

/**
 * Convert Base64 string to Uint8Array
 */
export function base64ToBuffer(base64: string): Uint8Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Store keys in localStorage
 * 
 * @param publicKey Base64-encoded public key
 * @param privateKey Base64-encoded private key (should be encrypted for production)
 */
export function storeKeysLocally(publicKey: string, privateKey: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      // Store public key
      window.localStorage.setItem('mlkem_public_key', publicKey);
      
      // Store private key (in production, this should be encrypted)
      window.localStorage.setItem('mlkem_private_key', privateKey);
      
      // Store metadata
      window.localStorage.setItem('mlkem_key_generated_at', new Date().toISOString());
      window.localStorage.setItem('mlkem_key_algorithm', 'Kyber768');
      
      console.log('Keys stored in localStorage successfully');
    }
  } catch (error) {
    console.error('Failed to store keys in localStorage:', error);
    throw error;
  }
}

/**
 * Retrieve stored keys from localStorage
 */
export function retrieveKeysLocally(): {
  publicKey: string | null;
  privateKey: string | null;
} {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const publicKey = window.localStorage.getItem('mlkem_public_key');
      const privateKey = window.localStorage.getItem('mlkem_private_key');
      
      return {
        publicKey,
        privateKey,
      };
    }
  } catch (error) {
    console.error('Failed to retrieve keys from localStorage:', error);
  }
  
  return {
    publicKey: null,
    privateKey: null,
  };
}

/**
 * Clear stored keys from localStorage (e.g., on logout)
 */
export function clearStoredKeys(): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem('mlkem_public_key');
      window.localStorage.removeItem('mlkem_private_key');
      window.localStorage.removeItem('mlkem_key_generated_at');
      window.localStorage.removeItem('mlkem_key_algorithm');
      
      console.log('Stored keys cleared from localStorage');
    }
  } catch (error) {
    console.error('Failed to clear keys from localStorage:', error);
  }
}

/**
 * Check if keys are already stored locally
 */
export function hasStoredKeys(): boolean {
  const { publicKey, privateKey } = retrieveKeysLocally();
  return !!publicKey && !!privateKey;
}

/**
 * Get key information/metadata
 */
export function getStoredKeyInfo(): {
  hasKeys: boolean;
  generatedAt: string | null;
  algorithm: string | null;
  publicKeySize: number;
  privateKeySize: number;
} {
  const { publicKey, privateKey } = retrieveKeysLocally();
  const generatedAt = typeof window !== 'undefined' 
    ? window.localStorage?.getItem('mlkem_key_generated_at') || null 
    : null;
  const algorithm = typeof window !== 'undefined' 
    ? window.localStorage?.getItem('mlkem_key_algorithm') || null 
    : null;
  
  // Estimate byte sizes from Base64 length (bytes = length * 3 / 4)
  const publicKeySize = publicKey ? Math.round(publicKey.length * 3 / 4) : 0;
  const privateKeySize = privateKey ? Math.round(privateKey.length * 3 / 4) : 0;
  
  return {
    hasKeys: !!publicKey && !!privateKey,
    generatedAt,
    algorithm,
    publicKeySize,
    privateKeySize,
  };
}
