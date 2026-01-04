import { api } from '../services/api';
import { base64ToBuffer } from '../services/crypto';
import { ensureUint8Array } from '../utils/buffer';
import { createMLDSA65 } from '@openforge-sh/liboqs';


export interface FileAttachmentMetadata {
  type: 'file';
  url: string;
  filename: string;
  size: number;
  encrypted_hash: string;
  file_key: string;
  file_iv: string;
  signer_public_key: string;
  file_hash: string;
  signature: string;
  signature_algorithm: string;
  hash_algorithm: string;
  mime_type: string;
  original_size: number;
  original_filename: string;
  uploaded_at: string;
}


export interface VerifiedFileResult {
  blob: Blob;
  filename: string;
  mimeType: string;
  size: number;
}


/**
 * GET zaszyfrowanego pliku jako Uint8Array.
 */
async function downloadEncryptedFile(url: string): Promise<Uint8Array> {
  const cleaned = url.replace(/^\/api\//, '/');
  const response = await api.get(cleaned, { responseType: 'arraybuffer' });
  return new Uint8Array(response.data as ArrayBuffer);
}


/**
 * Sprawdzenie SHA-256 zaszyfrowanego bloba.
 */
async function verifyEncryptedHash(
  encryptedBytes: Uint8Array,
  expectedHex: string
): Promise<boolean> {
  const safeBytes = ensureUint8Array(encryptedBytes);
  const digest = await crypto.subtle.digest('SHA-256', safeBytes.buffer.slice(safeBytes.byteOffset, safeBytes.byteOffset + safeBytes.byteLength) as ArrayBuffer);
  const hashBytes = new Uint8Array(digest);
  const hex = Array.from(hashBytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');

  return hex === expectedHex.toLowerCase();
}


/**
 * Deszyfruje AES-GCM 256 RAW_PAYLOAD.
 */
async function decryptPayload(
  fileKeyB64: string,
  fileIvB64: string,
  encryptedBytes: Uint8Array
): Promise<Uint8Array> {
  const keyBytes = ensureUint8Array(base64ToBuffer(fileKeyB64));
  const ivBytes = ensureUint8Array(base64ToBuffer(fileIvB64));
  const safeEncryptedBytes = ensureUint8Array(encryptedBytes);
  const keyBuffer = keyBytes.buffer.slice(keyBytes.byteOffset, keyBytes.byteOffset + keyBytes.byteLength) as ArrayBuffer;
  const ivBuffer = ivBytes.buffer.slice(ivBytes.byteOffset, ivBytes.byteOffset + ivBytes.byteLength) as ArrayBuffer;
  const encryptedBuffer = safeEncryptedBytes.buffer.slice(safeEncryptedBytes.byteOffset, safeEncryptedBytes.byteOffset + safeEncryptedBytes.byteLength) as ArrayBuffer;
  const key = await crypto.subtle.importKey(
    'raw',
    keyBuffer,
    { name: 'AES-GCM' },
    false,
    ['decrypt']
  );

  const decrypted = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: ivBuffer },
    key,
    encryptedBuffer
  );

  return new Uint8Array(decrypted);
}


/**
 * Parsuje RAW_PAYLOAD = [SigLen(4B)|MetaLen(4B)|Meta|Sig|File].
 */
function unpackRawPayload(raw: Uint8Array): {
  meta: Record<string, unknown>;
  fileBytes: Uint8Array;
} {
  if (raw.length < 8) {
    throw new Error('RAW payload too short');
  }

  const view = new DataView(raw.buffer, raw.byteOffset, raw.byteLength);
  const sigLen = view.getUint32(0, false);
  const metaLen = view.getUint32(4, false);
  const headerEnd = 8;
  const metaStart = headerEnd;
  const metaEnd = metaStart + metaLen;
  const sigStart = metaEnd;
  const sigEnd = sigStart + sigLen;

  if (sigEnd > raw.length) {
    throw new Error('RAW payload corrupted (lengths out of range)');
  }

  const metaBytes = raw.subarray(metaStart, metaEnd);
  const fileBytes = raw.subarray(sigEnd);
  const metaJson = new TextDecoder().decode(metaBytes);
  const meta = JSON.parse(metaJson) as Record<string, unknown>;


  return { meta, fileBytes };
}


/**
 * SHA-256 oryginalnego pliku i porównanie z file_hash (Base64).
 */
async function verifyFileHash(
  fileBytes: Uint8Array,
  expectedHashB64: string
): Promise<boolean> {
  const safeFileBytes = ensureUint8Array(fileBytes);
  const fileBuffer = safeFileBytes.buffer.slice(safeFileBytes.byteOffset, safeFileBytes.byteOffset + safeFileBytes.byteLength) as ArrayBuffer;
  const digest = await crypto.subtle.digest('SHA-256', fileBuffer);
  const hashBytes = new Uint8Array(digest);
  const expected = ensureUint8Array(base64ToBuffer(expectedHashB64));
  if (expected.length !== hashBytes.length) return false;


  for (let i = 0; i < hashBytes.length; i++) {
    if (hashBytes[i] !== expected[i]) return false;
  }
  return true;
}


/**
 * Weryfikacja podpisu ML-DSA-65 (liboqs) nad hashem pliku.
 */
async function verifySignature(
  fileBytes: Uint8Array,
  signatureB64: string,
  signerPubKeyB64: string
): Promise<boolean> {
  const sig = await createMLDSA65();
  const safeFileBytes = ensureUint8Array(fileBytes);
  const fileBuffer = safeFileBytes.buffer.slice(safeFileBytes.byteOffset, safeFileBytes.byteOffset + safeFileBytes.byteLength) as ArrayBuffer;
  const digest = await crypto.subtle.digest('SHA-256', fileBuffer);
  const hashBytes = new Uint8Array(digest);
  const signatureBytes = ensureUint8Array(base64ToBuffer(signatureB64));
  const pubKeyBytes = ensureUint8Array(base64ToBuffer(signerPubKeyB64));

  return sig.verify(hashBytes, signatureBytes, pubKeyBytes);
}


/**
 * Główna funkcja: pobiera, weryfikuje i odszyfrowuje załącznik.
 */
export type AttachmentVerifyErrorCode =
  | 'ENCRYPTED_HASH_MISMATCH'
  | 'FILE_HASH_MISMATCH'
  | 'SIGNATURE_INVALID'
  | 'DECRYPT_FAILED'
  | 'UNKNOWN';


export class AttachmentVerifyError extends Error {
  code: AttachmentVerifyErrorCode;
  constructor(code: AttachmentVerifyErrorCode, message: string) {
    super(message);
    this.code = code;
    this.name = 'AttachmentVerifyError';
  }
}


export async function downloadAndVerifyAttachment(
  meta: FileAttachmentMetadata
): Promise<VerifiedFileResult> {
  const encryptedBytes = await downloadEncryptedFile(meta.url);

  let encOk: boolean;
  try {
    encOk = await verifyEncryptedHash(encryptedBytes, meta.encrypted_hash);
  } catch (e) {
    throw new AttachmentVerifyError('UNKNOWN', 'Failed to compute encrypted blob hash');
  }
  if (!encOk) {
    throw new AttachmentVerifyError('ENCRYPTED_HASH_MISMATCH', 'Encrypted blob hash mismatch');
  }

  let rawPayload: Uint8Array;
  try {
    rawPayload = await decryptPayload(meta.file_key, meta.file_iv, encryptedBytes);
  } catch (e) {
    throw new AttachmentVerifyError('DECRYPT_FAILED', 'Failed to decrypt file payload');
  }

  let unpacked;
  try {
    unpacked = unpackRawPayload(rawPayload);
  } catch (e) {
    throw new AttachmentVerifyError('UNKNOWN', 'Failed to unpack RAW payload');
  }

  const { meta: innerMeta, fileBytes } = unpacked;

  let hashOk: boolean;
  try {
    hashOk = await verifyFileHash(fileBytes, meta.file_hash);
  } catch (e) {
    throw new AttachmentVerifyError('UNKNOWN', 'Failed to compute file hash');
  }
  if (!hashOk) {
    throw new AttachmentVerifyError('FILE_HASH_MISMATCH', 'File hash mismatch');
  }

  let sigOk: boolean;
  try {
    sigOk = await verifySignature(fileBytes, meta.signature, meta.signer_public_key);
  } catch (e) {
    throw new AttachmentVerifyError('UNKNOWN', 'Failed to verify signature');
  }
  if (!sigOk) {
    throw new AttachmentVerifyError('SIGNATURE_INVALID', 'File signature invalid');
  }

  const mimeType = (innerMeta.mime_type as string) || meta.mime_type || 'application/octet-stream';
  const filename = (innerMeta.filename as string) || meta.original_filename || 'attachment';
  const size = (innerMeta.size as number) || meta.original_size || fileBytes.length;
  const safeFileBytes = ensureUint8Array(fileBytes);
  const fileBuffer = safeFileBytes.buffer.slice(safeFileBytes.byteOffset, safeFileBytes.byteOffset + safeFileBytes.byteLength) as ArrayBuffer;
  const blob = new Blob([fileBuffer], { type: mimeType as string });

  return {
    blob,
    filename,
    mimeType,
    size,
  };
}
