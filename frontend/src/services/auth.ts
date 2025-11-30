import { api } from './api'
import { socket } from './socket'

const TIMEOUT_MS = 5000

/**
 * Initializes authentication after a token is obtained
 * Sets up API headers and connects WebSocket with authentication
 */
export const initializeAuth = async (token: string): Promise<void> => {
  try {
    // Set API authorization header
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } catch (err) {
    console.warn('Failed to set default API authorization header', err)
  }

  try {
    // Set Socket.IO authentication
    const bearer = `Bearer ${token}`
    ;(socket as any).auth = { token: bearer }

    // Connect socket if not already connected
    if (!socket.connected) {
      socket.connect()
    }

    // Wait for socket connection
    await waitForSocketConnection()
  } catch (err) {
    console.warn('Failed to initialize socket connection', err)
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
