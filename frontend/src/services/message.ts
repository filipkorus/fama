import { retrieveKeysLocally } from './crypto'
import { MlKem768 } from 'mlkem'

export interface EncryptedContentResult {
  encryptedContent: string
  nonce: string
}

export interface EncryptedSessionKeyResult {
  capsule: string             // ML-KEM Capsule
  encryptedSecret: string     // AES Session Key encrypted with KEK
  nonce: string              // IV used for encrypting the Session Key
}

function generateNonce(): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(12))
}

export function toBase64(buffer: Uint8Array): string {
  let binary = ''
  const bytes = new Uint8Array(buffer)
  const len = bytes.byteLength
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

export function fromBase64(base64: string): Uint8Array {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

function ensureProperBuffer(arr: Uint8Array): Uint8Array {
  if (typeof SharedArrayBuffer !== 'undefined' && arr.buffer instanceof SharedArrayBuffer) {
    return new Uint8Array(arr)
  }
  return arr
}

/**
 * 1. Generate a brand new AES-256 Session Key.
 * Returns the raw key bytes as Base64.
 */
export async function generateSessionKey(): Promise<string> {
  const key = await crypto.subtle.generateKey(
    {
      name: 'AES-GCM',
      length: 256,
    },
    true,
    ['encrypt', 'decrypt']
  )
  
  const raw = await crypto.subtle.exportKey('raw', key)
  return toBase64(new Uint8Array(raw))
}

/**
 * 2. Encrypt the Session Key for the Recipient using ML-KEM.
 * * Logic:
 * A. Generate KEK (Key Encryption Key) via ML-KEM Encap.
 * B. Encrypt the Session Key (AES) using the KEK (AES).
 */
export async function encryptSessionKeyForRecipient(
  sessionKeyBase64: string,
  recipientPublicKeyBase64: string
): Promise<EncryptedSessionKeyResult> {
  try {
    // A. ML-KEM Encapsulation -> Get KEK
    const sender = new MlKem768()
    const recipientPubKeyBytes = fromBase64(recipientPublicKeyBase64)
    const [ct, sharedSecretKEK] = await sender.encap(recipientPubKeyBytes) // ct=Capsule, ss=KEK

    // B. Import KEK as an AES-GCM Key
    // FIX: Rzutowanie na 'any' naprawia błąd TypeScript "ArrayBufferLike"
    const kekKey = await crypto.subtle.importKey(
      'raw',
      ensureProperBuffer(sharedSecretKEK) as any, 
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt']
    )

    // C. Encrypt the actual Session Key using KEK
    const sessionKeyBytes = fromBase64(sessionKeyBase64)
    const nonce = generateNonce()
    
    const encryptedSessionKeyBuffer = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: nonce as any }, // FIX: Rzutowanie nonce
      kekKey,
      sessionKeyBytes as any // FIX: Rzutowanie danych
    )

    return {
      capsule: toBase64(ct),
      encryptedSecret: toBase64(new Uint8Array(encryptedSessionKeyBuffer)),
      nonce: toBase64(nonce)
    }
  } catch (error) {
    console.error('Failed to encrypt session key:', error)
    throw error
  }
}

/**
 * 3. Decrypt the Session Key received from Sender.
 * * Logic:
 * A. Recover KEK via ML-KEM Decap (using our Private Key).
 * B. Decrypt the Session Key using KEK.
 */
export async function decryptSessionKeyFromSender(
  capsuleBase64: string,
  encryptedSecretBase64: string,
  nonceBase64: string
): Promise<string> {
  try {
    // Get Local Private Key
    const { privateKey: privateKeyBase64 } = retrieveKeysLocally()
    if (!privateKeyBase64) throw new Error("No private key found")

    // A. ML-KEM Decapsulation -> Get KEK
    const recipient = new MlKem768()
    const capsuleBytes = fromBase64(capsuleBase64)
    const privateKeyBytes = fromBase64(privateKeyBase64)
    
    const sharedSecretKEK = await recipient.decap(capsuleBytes, privateKeyBytes)

    // B. Import KEK
    // FIX: Rzutowanie na 'any'
    const kekKey = await crypto.subtle.importKey(
      'raw',
      ensureProperBuffer(sharedSecretKEK) as any,
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt']
    )

    // C. Decrypt the Session Key
    const encryptedSecretBytes = fromBase64(encryptedSecretBase64)
    const nonceBytes = fromBase64(nonceBase64)

    const sessionKeyRawBuffer = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: nonceBytes as any }, // FIX: Rzutowanie iv
      kekKey,
      encryptedSecretBytes as any // FIX: Rzutowanie danych
    )

    return toBase64(new Uint8Array(sessionKeyRawBuffer))
  } catch (error) {
    console.error('Failed to decrypt session key:', error)
    throw error
  }
}

/**
 * 4. Encrypt a text message using the established Session Key (AES-GCM).
 */
export async function encryptMessage(
  sessionKeyBase64: string,
  plainText: string
): Promise<EncryptedContentResult> {
  try {
    const sessionKeyBytes = fromBase64(sessionKeyBase64)
    // FIX: Rzutowanie klucza
    const key = await crypto.subtle.importKey(
      'raw',
      sessionKeyBytes as any,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt']
    )

    const nonce = generateNonce()
    const encoder = new TextEncoder()
    const data = encoder.encode(plainText)

    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: nonce as any }, // FIX: Rzutowanie iv
      key,
      data as any // FIX: Rzutowanie danych
    )

    return {
      encryptedContent: toBase64(new Uint8Array(encrypted)),
      nonce: toBase64(nonce)
    }
  } catch (error) {
    console.error('Message encryption failed:', error)
    throw error
  }
}

/**
 * 5. Decrypt a text message using the established Session Key (AES-GCM).
 */
export async function decryptMessage(
  sessionKeyBase64: string,
  encryptedContentBase64: string,
  nonceBase64: string
): Promise<string> {
  try {
    const sessionKeyBytes = fromBase64(sessionKeyBase64)
    // FIX: Rzutowanie klucza
    const key = await crypto.subtle.importKey(
      'raw',
      sessionKeyBytes as any,
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt']
    )

    const encryptedBytes = fromBase64(encryptedContentBase64)
    const nonceBytes = fromBase64(nonceBase64)

    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: nonceBytes as any }, // FIX: Rzutowanie iv
      key,
      encryptedBytes as any // FIX: Rzutowanie danych
    )

    const decoder = new TextDecoder()
    return decoder.decode(decrypted)
  } catch (error) {
    // console.error('Message decryption failed:', error)
    throw error
  }
}
