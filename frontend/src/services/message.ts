import { api } from './api'
import { retrieveKeysLocally } from './crypto'
import { getPublicKeyFromCache, cachePublicKey, hasPublicKeyInCache } from './publicKeyCache'
import { MlKem768 } from 'mlkem'
import User from '../types/User.ts'

interface PublicKeyResponse {
  user_id: number
  username: string
  public_key: string
}

interface EncryptedMessagePayload {
  recipient_id: number
  encrypted_content: string
  capsule_mlkem: string
  nonce: string
}

/**
 * Fetch user's public key by username
 */
export async function fetchPublicKeyByUsername(username: string): Promise<PublicKeyResponse> {
  try {
    const response = await api.get<PublicKeyResponse>(`/users/${username}/public-key`)
    return response.data
  } catch (error) {
    console.error(`Failed to fetch public key for user ${username}:`, error)
    throw error
  }
}

/**
 * Fetch user's public key by user ID
 */
export async function fetchPublicKeyByUserId(userId: number): Promise<PublicKeyResponse> {
  try {
    const response = await api.get<PublicKeyResponse>(`/users/${userId}/public-key`)
    return response.data
  } catch (error) {
    console.error(`Failed to fetch public key for user ${userId}:`, error)
    throw error
  }
}

/**
 * Generate random nonce for AES-GCM
 */
function generateNonce(): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(12))
}

/**
 * Convert Uint8Array to Base64
 */
function toBase64(buffer: Uint8Array): string {
  let binary = ''
  const chunkSize = 0x8000
  for (let i = 0; i < buffer.length; i += chunkSize) {
    const chunk = buffer.subarray(i, i + chunkSize)
    binary += String.fromCharCode(...Array.from(chunk))
  }
  return btoa(binary)
}

/**
 * Convert Base64 string to Uint8Array
 */
function fromBase64(base64: string): Uint8Array {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

/**
 * Ensure Uint8Array has proper buffer (fix ArrayBufferLike type issue)
 */
function ensureProperBuffer(arr: Uint8Array): Uint8Array {
  // Check if buffer is SharedArrayBuffer (if it exists in the environment)
  if (typeof SharedArrayBuffer !== 'undefined' && arr.buffer instanceof SharedArrayBuffer) {
    // Convert SharedArrayBuffer to regular ArrayBuffer
    return new Uint8Array(arr)
  }
  return arr
}

/**
 * Encrypt message using ML-KEM for key encapsulation + AES-GCM for content
 */
async function encryptMessageWithMLKem(
  message: string,
  recipientPublicKeyBase64: string,
  nonce: Uint8Array
): Promise<{
  encrypted: string
  capsule: string
}> {
  try {
    // 1. Initialize ML-KEM sender
    const sender = new MlKem768()

    // 2. Convert recipient's public key from Base64 to Uint8Array
    const recipientPublicKeyBytes = fromBase64(recipientPublicKeyBase64)

    // 3. Encapsulate - generates shared secret and capsule
    // ct = capsule (ciphertext)
    // ssS = shared secret (will be used as AES key)
    const [ct, ssS] = await sender.encap(recipientPublicKeyBytes)

    console.log(`ML-KEM Encapsulation: capsule=${ct.length} bytes, shared_secret=${ssS.length} bytes`)

    // 4. Import shared secret as AES key
    const aesKey = await crypto.subtle.importKey(
      'raw',
      ensureProperBuffer(ssS) as any,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt']
    )

    // 5. Encode message
    const encoder = new TextEncoder()
    const messageBytes = encoder.encode(message)

    // 6. Encrypt with AES-GCM using the shared secret
    const encryptedData = await crypto.subtle.encrypt(
      {
        name: 'AES-GCM',
        iv: ensureProperBuffer(nonce) as any,
      },
      aesKey,
      messageBytes
    )

    // 7. Convert to Base64
    const encryptedBase64 = toBase64(new Uint8Array(encryptedData))
    const capsuleBase64 = toBase64(ct)

    return {
      encrypted: encryptedBase64,
      capsule: capsuleBase64,
    }
  } catch (error) {
    console.error('Failed to encrypt message with ML-KEM:', error)
    throw error
  }
}

/**
 * Send encrypted message via WebSocket
 */
export async function sendEncryptedMessage(
  socket: any,
  recipientUsername: string,
  message: string
): Promise<void> {
  try {
    // 1. Get or fetch recipient's public key
    console.log(`Getting public key for ${recipientUsername}...`)
    
    let recipientData: PublicKeyResponse
    
    if (hasPublicKeyInCache(recipientUsername)) {
      // Use cached key
      const cached = getPublicKeyFromCache(recipientUsername)
      if (cached) {
        recipientData = {
          user_id: cached.user_id,
          username: cached.username,
          public_key: cached.public_key,
        }
        console.log(`Using cached public key for ${recipientUsername}`)
      } else {
        // Shouldn't happen, but fallback to fetch
        recipientData = await fetchPublicKeyByUsername(recipientUsername)
      }
    } else {
      // Fetch from API
      recipientData = await fetchPublicKeyByUsername(recipientUsername)
      // Cache it for future use
      cachePublicKey(recipientData)
      console.log(`Cached new public key for ${recipientUsername}`)
    }

    // 2. Generate nonce for AES-GCM
    const nonce = generateNonce()

    // 3. Encrypt message with ML-KEM + AES-GCM
    const { encrypted, capsule } = await encryptMessageWithMLKem(
      message,
      recipientData.public_key,
      nonce
    )

    // 4. Send via WebSocket
    const payload: EncryptedMessagePayload = {
      recipient_id: recipientData.user_id,
      encrypted_content: encrypted,
      capsule_mlkem: capsule,
      nonce: toBase64(nonce),
    }

    console.log('Sending encrypted message:', {
      recipient_id: payload.recipient_id,
      encrypted_content_length: payload.encrypted_content.length,
      capsule_length: payload.capsule_mlkem.length,
      nonce_length: payload.nonce.length,
    })

    socket.emit('send_message', payload)
  } catch (error) {
    console.error('Failed to send encrypted message:', error)
    throw error
  }
}

/**
 * Decrypt message received from another user
 * 
 * @param capsuleBase64 - ML-KEM capsule (from sender) as Base64
 * @param encryptedContentBase64 - Encrypted message content as Base64
 * @param nonceBase64 - AES-GCM nonce as Base64
 * @returns Decrypted plaintext message
 */
export async function decryptMessage(
  capsuleBase64: string,
  encryptedContentBase64: string,
  nonceBase64: string
): Promise<string> {
  try {
    // 1. Get stored private key
    const { privateKey: privateKeyBase64 } = retrieveKeysLocally()
    if (!privateKeyBase64) {
      throw new Error('No private key stored locally')
    }

    // 2. Convert inputs from Base64
    const capsuleBytes = fromBase64(capsuleBase64)
    const encryptedBytes = fromBase64(encryptedContentBase64)
    const nonce = fromBase64(nonceBase64)
    const privateKeyBytes = fromBase64(privateKeyBase64)

    // 3. Initialize ML-KEM recipient
    const recipient = new MlKem768()

    // 4. Decapsulate - recover shared secret using private key and capsule
    const sharedSecret = await recipient.decap(capsuleBytes, privateKeyBytes)

    console.log(`ML-KEM Decapsulation: shared_secret=${sharedSecret.length} bytes`)

    // 5. Import shared secret as AES key
    const aesKey = await crypto.subtle.importKey(
      'raw',
      ensureProperBuffer(sharedSecret) as any,
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt']
    )

    // 6. Decrypt with AES-GCM
    const decryptedData = await crypto.subtle.decrypt(
      {
        name: 'AES-GCM',
        iv: ensureProperBuffer(nonce) as any,
      },
      aesKey,
      encryptedBytes as any
    )

    const decoder = new TextDecoder()
    const plainText = decoder.decode(decryptedData)

    console.log('Message decrypted successfully')
    return plainText
  } catch (error) {
    console.error('Failed to decrypt message:', error)
    throw error
  }
}

/**
 * Preload public key for a user (call when entering chat with that user)
 */
export async function preloadPublicKey(username: string): Promise<void> {
  try {
    if (!hasPublicKeyInCache(username)) {
      console.log(`Preloading public key for ${username}...`)
      const publicKeyData = await fetchPublicKeyByUsername(username)
      cachePublicKey(publicKeyData)
      console.log(`Successfully preloaded and cached public key for ${username}`)
    } else {
      console.log(`Public key for ${username} already in cache`)
    }
  } catch (error) {
    console.error(`Failed to preload public key for ${username}:`, error)
    // Don't throw - cache miss will be handled on send
  }
}
export function getUserIdByUsername(username: string, allUsers: User[]): number | null {
  const user = allUsers.find((u) => u.username === username)
  return user ? user.id : null
}
