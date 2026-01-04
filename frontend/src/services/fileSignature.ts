import { createMLDSA65 } from '@openforge-sh/liboqs';
import { base64ToBuffer } from './crypto';

const DIL_PUB_KEY_STORAGE = 'dilithium_public_key';
const DIL_PRIV_KEY_STORAGE = 'dilithium_private_key';
const DIL_META_ALGO = 'dilithium_key_algorithm';
const DIL_META_CREATED = 'dilithium_key_generated_at';
const DIL_ALGO = 'ML-DSA-65';
import { toUint8Array } from '../utils/buffer';

let mldsaInstance: Awaited<ReturnType<typeof createMLDSA65>> | null = null;

export interface DilithiumKeypair {
  publicKey: string;
  privateKey: string;
}

export interface FileSignaturePayload {
  file_hash: string;
  hash_algorithm: string;
  signature: string;
  signature_algorithm: string;
  signer_public_key: string;
}

/**
 * Lazy init instancji ML-DSA-65 (liboqs WASM).
 */
async function getMLDSA(): Promise<Awaited<ReturnType<typeof createMLDSA65>>> {
  if (!mldsaInstance) {
    mldsaInstance = await createMLDSA65();
  }
  return mldsaInstance;
}

/**
 * Generuje parę kluczy ML-DSA-65 (Dilithium-like) przy użyciu liboqs.
 */
export async function generateDilithiumKeypair(): Promise<DilithiumKeypair> {
  try {
    const sig = await getMLDSA();
    const { publicKey, secretKey } = sig.generateKeyPair();

    console.log('[ML-DSA/liboqs] Keypair generated', {
      publicKeyBytes: publicKey.length,
      privateKeyBytes: secretKey.length,
    });

    const publicKeyB64 = bufferToBase64(publicKey);
    const privateKeyB64 = bufferToBase64(secretKey);

    return { publicKey: publicKeyB64, privateKey: privateKeyB64 };
  } catch (error) {
    console.error('[ML-DSA/liboqs] Failed to generate keys:', error);
    throw new Error('Failed to generate Dilithium (ML-DSA) keys');
  }
}

export function storeDilithiumKeys(publicKey: string, privateKey: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(DIL_PUB_KEY_STORAGE, publicKey);
      window.localStorage.setItem(DIL_PRIV_KEY_STORAGE, privateKey);
      window.localStorage.setItem(DIL_META_CREATED, new Date().toISOString());
      window.localStorage.setItem(DIL_META_ALGO, DIL_ALGO);
    }
  } catch (error) {
    console.error('[ML-DSA/liboqs] Failed to store keys:', error);
    throw error;
  }
}

export function retrieveDilithiumKeys(): DilithiumKeypair | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const publicKey = window.localStorage.getItem(DIL_PUB_KEY_STORAGE);
      const privateKey = window.localStorage.getItem(DIL_PRIV_KEY_STORAGE);
      if (!publicKey || !privateKey) return null;
      return { publicKey, privateKey };
    }
  } catch (error) {
    console.error('[ML-DSA/liboqs] Failed to retrieve keys:', error);
  }
  return null;
}

export function getDilithiumPrivateKeyBytes(): Uint8Array | null {
  const keys = retrieveDilithiumKeys();
  if (!keys) return null;
  return base64ToBuffer(keys.privateKey);
}

export function getDilithiumPublicKeyBytes(): Uint8Array | null {
  const keys = retrieveDilithiumKeys();
  if (!keys) return null;
  return base64ToBuffer(keys.publicKey);
}

/**
 * Hash pliku SHA-256.
 */
export async function computeFileHash(file: File): Promise<Uint8Array> {
  const buffer = await file.arrayBuffer();
  const data = new Uint8Array(buffer);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return toUint8Array(digest);
}

/**
 * Podpisuje hash pliku prywatnym kluczem ML-DSA-65 (liboqs).
 */
export async function signFile(file: File): Promise<FileSignaturePayload> {
  const keys = retrieveDilithiumKeys();
  if (!keys) {
    throw new Error('Dilithium (ML-DSA) keys not available in browser storage');
  }

  const privKey = base64ToBuffer(keys.privateKey);
  const pubKey = base64ToBuffer(keys.publicKey);
  const sig = await getMLDSA();
  const hashBytes = await computeFileHash(file);
  const signatureBytes = sig.sign(hashBytes, privKey);

  return {
    file_hash: bufferToBase64(hashBytes),
    hash_algorithm: 'SHA256',
    signature: bufferToBase64(signatureBytes),
    signature_algorithm: DIL_ALGO,
    signer_public_key: bufferToBase64(pubKey),
  };
}

/**
 * Wariant do pakowania RAW_PAYLOAD – zwraca surowe bajty podpisu i hash.
 */
export async function signFileRaw(
  fileBytes: any
): Promise<{ hashBytes: Uint8Array; signatureBytes: Uint8Array; publicKeyBytes: Uint8Array }> {
  const keys = retrieveDilithiumKeys();
  if (!keys) {
    throw new Error('Dilithium (ML-DSA) keys not available in browser storage');
  }

  const privKey = base64ToBuffer(keys.privateKey);
  const pubKey = base64ToBuffer(keys.publicKey);
  const sig = await getMLDSA();

  const digest = await crypto.subtle.digest('SHA-256', fileBytes);
  const hashBytes = new Uint8Array(digest as any);

  const signatureBytes = sig.sign(hashBytes, privKey);

  return { hashBytes, signatureBytes, publicKeyBytes: pubKey };
}

/**
 * Weryfikacja podpisu pliku po stronie klienta (ML-DSA-65 / liboqs).
 */
export async function verifyFileSignature(
  file: File,
  payload: FileSignaturePayload
): Promise<boolean> {
  if (payload.hash_algorithm !== 'SHA256' || payload.signature_algorithm !== DIL_ALGO) {
    console.warn('[FileSignature/liboqs] Unsupported algorithm in payload', payload);
    return false;
  }

  const hashBytes = await computeFileHash(file);
  const signatureBytes = base64ToBuffer(payload.signature);
  const pubKeyBytes = base64ToBuffer(payload.signer_public_key);

  const sig = await getMLDSA();

  return sig.verify(hashBytes, signatureBytes, pubKeyBytes);
}

function bufferToBase64(buffer: Uint8Array): string {
  let binary = '';
  const chunkSize = 0x8000;
  for (let i = 0; i < buffer.length; i += chunkSize) {
    const chunk = buffer.subarray(i, i + chunkSize);
    binary += String.fromCharCode.apply(null, Array.from(chunk) as any);
  }
  return btoa(binary);
}
