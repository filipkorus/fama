/**
 * Local cache for public keys of users
 * Stores public keys in memory to avoid redundant API calls
 * Assumption: public keys don't change during session
 */

interface CachedPublicKey {
  user_id: number
  username: string
  public_key: string
  cached_at: number
}

const publicKeyCache = new Map<string, CachedPublicKey>()

/**
 * Get public key from cache by username
 */
export function getPublicKeyFromCache(username: string): CachedPublicKey | undefined {
  return publicKeyCache.get(username)
}

/**
 * Get public key from cache by user ID
 */
export function getPublicKeyFromCacheById(userId: number): CachedPublicKey | undefined {
  for (const entry of publicKeyCache.values()) {
    if (entry.user_id === userId) {
      return entry
    }
  }
  return undefined
}

/**
 * Store public key in cache
 */
export function cachePublicKey(data: {
  user_id: number
  username: string
  public_key: string
}): void {
  publicKeyCache.set(data.username, {
    ...data,
    cached_at: Date.now(),
  })
}

/**
 * Check if public key exists in cache
 */
export function hasPublicKeyInCache(username: string): boolean {
  return publicKeyCache.has(username)
}

/**
 * Get all cached public keys
 */
export function getAllCachedPublicKeys(): CachedPublicKey[] {
  return Array.from(publicKeyCache.values())
}

/**
 * Clear all cached public keys
 */
export function clearPublicKeyCache(): void {
  publicKeyCache.clear()
}

/**
 * Get cache statistics
 */
export function getPublicKeyCacheStats(): {
  size: number
  usernames: string[]
} {
  return {
    size: publicKeyCache.size,
    usernames: Array.from(publicKeyCache.keys()),
  }
}
