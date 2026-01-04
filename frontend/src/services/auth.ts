import { api } from './api'
import { socket } from './socket'
import axios from 'axios'
import { API_URL } from '../config'

const TIMEOUT_MS = 5000

/**
 * Checks if a JWT token is expired or about to expire soon
 * @param token JWT token to check
 * @returns true if token is expired or expires within 30 seconds
 */
const isTokenExpired = (token: string): boolean => {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return true

    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(base64))

    if (!payload.exp) return true

    // Consider token expired if it expires within 30 seconds
    const expirationTime = payload.exp * 1000
    const currentTime = Date.now()
    const bufferTime = 30 * 1000 // 30 seconds buffer

    return expirationTime - currentTime < bufferTime
  } catch (e) {
    console.error('Failed to parse token:', e)
    return true
  }
}

/**
 * Attempts to refresh the access token using the refresh token cookie
 * @returns New access token or null if refresh failed
 */
export const refreshAccessToken = async (): Promise<string | null> => {
  try {
    const { data } = await axios.post(
      `${API_URL}/api/auth/refresh`,
      {},
      { withCredentials: true }
    )

    const newToken = data.access_token as string
    if (newToken) {
      const username = getStoredUsername() || ''
      storeAuthData(newToken, username)
      return newToken
    }
    return null
  } catch (error) {
    console.error('Failed to refresh token:', error)
    return null
  }
}

/**
 * Validates and refreshes token if needed before use
 * @param token Current token
 * @returns Valid token or null if validation/refresh failed
 */
export const ensureValidToken = async (token: string): Promise<string | null> => {
  if (!token) return null

  if (isTokenExpired(token)) {
    console.log('Token expired, attempting refresh...')
    return await refreshAccessToken()
  }

  return token
}

/**
 * Initializes authentication after a token is obtained
 * Sets up API headers and connects WebSocket with authentication
 * Automatically refreshes expired tokens before connecting
 */
export const initializeAuth = async (token: string): Promise<void> => {
  // Validate and refresh token if needed
  const validToken = await ensureValidToken(token)

  if (!validToken) {
    console.warn('Failed to obtain valid token')
    clearAuthData()
    throw new Error('Invalid or expired token')
  }

  try {
    // Set API authorization header
    api.defaults.headers.common['Authorization'] = `Bearer ${validToken}`
  } catch (err) {
    console.warn('Failed to set default API authorization header', err)
  }

  try {
    // Set Socket.IO authentication
    const bearer = `Bearer ${validToken}`
    ;(socket as any).auth = { token: bearer }

    // Connect socket if not already connected
    if (!socket.connected) {
      socket.connect()
    }

    // Wait for socket connection
    await waitForSocketConnection()
  } catch (err) {
    console.warn('Failed to initialize socket connection', err)
    throw err
  }
}

/**
 * Waits for WebSocket to connect with a timeout
 */
const waitForSocketConnection = (): Promise<void> => {
  return new Promise<void>((resolve, reject) => {
    if (socket.connected) {
      resolve()
      return
    }

    const onConnect = () => {
      socket.off('connect', onConnect)
      clearTimeout(timer)
      resolve()
    }

    const timer = setTimeout(() => {
      socket.off('connect', onConnect)
      reject(new Error('Timed out waiting for socket connection'))
    }, TIMEOUT_MS)

    socket.on('connect', onConnect)
  })
}

/**
 * Stores authentication data in localStorage
 */
export const storeAuthData = (token: string, username: string): void => {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem('auth', 'true')
    window.localStorage.setItem('username', username)
    window.localStorage.setItem('authToken', token)
  }
}

/**
 * Clears all authentication data from localStorage
 */
export const clearAuthData = (): void => {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem('auth')
    window.localStorage.removeItem('username')
    window.localStorage.removeItem('authToken')
  }
}

/**
 * Gets stored authentication token
 */
export const getStoredToken = (): string | null => {
  if (typeof window !== 'undefined') {
    return window.localStorage.getItem('authToken')
  }
  return null
}

/**
 * Gets stored username
 */
export const getStoredUsername = (): string | null => {
  if (typeof window !== 'undefined') {
    return window.localStorage.getItem('username')
  }
  return null
}

/**
 * Logs out user and disconnects socket
 */
export const logout = (): void => {
  clearAuthData()
  
  try {
    if (socket) {
      try {
        ;(socket as any).auth = {}
      } catch (e) {
        /* ignore */
      }
      if (socket.connected) {
        socket.disconnect()
      }
    }
  } catch (err) {
    console.warn('Error disconnecting socket on logout', err)
  }
}
