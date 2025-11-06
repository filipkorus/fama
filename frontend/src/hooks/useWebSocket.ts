import { useState, useEffect, useCallback } from 'react'
import { socket } from '../services/socket'

interface MessageData {
  from?: string
  message?: string
  type?: 'broadcast' | 'private'
  to?: string
  echo?: boolean
}

interface UseWebSocketReturn {
  isConnected: boolean
  sendMessage: (message: string, to?: string) => void
  messages: string[]
  username: string | null
  register: (username: string) => void
}

/**
 * Custom hook for managing WebSocket connection
 *
 * @returns {UseWebSocketReturn} Connection state, send message function and messages list
 *
 * @example
 * ```tsx
 * const { isConnected, sendMessage, messages, register } = useWebSocket()
 *
 * // Register user
 * register('Alice')
 *
 * // Send broadcast message
 * sendMessage('Hello, everyone!')
 *
 * // Send private message
 * sendMessage('Hi Bob!', 'Bob')
 * ```
 */
export const useWebSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<string[]>([])
  const [username, setUsername] = useState<string | null>(null)

  useEffect(() => {
    // Handle connection
    const onConnect = () => {
      setIsConnected(true)
      console.log('Connected to WebSocket server')
    }

    // Handle disconnection
    const onDisconnect = () => {
      setIsConnected(false)
      console.log('Disconnected from server')
    }

    // Handle incoming messages from server
    const onMessage = (data: string | MessageData) => {
      // Handle both string and object formats
      if (typeof data === 'string') {
        setMessages((prev) => [...prev, data])
      } else if (data && typeof data === 'object') {
        const msgText = data.message || ''
        const from = data.from || 'Server'
        const type = data.type || 'broadcast'
        const isPrivate = type === 'private'
        const isEcho = data.echo

        let displayMsg = ''
        if (isEcho) {
          displayMsg = `You: ${msgText}`
        } else if (isPrivate) {
          displayMsg = `[Private] ${from}: ${msgText}`
        } else if (data.to) {
          displayMsg = `You to ${data.to}: ${msgText}`
        } else {
          displayMsg = `${from}: ${msgText}`
        }

        setMessages((prev) => [...prev, displayMsg])
      }
    }

    // Handle registration confirmation
    const onRegistered = (data: any) => {
      setUsername(data.username)
      console.log('Registered as:', data.username)
    }

    // Register event handlers
    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('message', onMessage)
    socket.on('registered', onRegistered)

    // Check initial connection state
    if (socket.connected) {
      setIsConnected(true)
    }

    // Cleanup - remove handlers on unmount
    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('message', onMessage)
      socket.off('registered', onRegistered)
    }
  }, [])

  // Function to register user
  const register = useCallback((username: string) => {
    socket.emit('register', { username })
  }, [])

  // Function to send messages
  const sendMessage = useCallback((message: string, to?: string) => {
    if (!message.trim()) return

    if (to) {
      // Send private message
      socket.emit('message', { message, to })
    } else {
      // Send broadcast message
      socket.emit('message', { message })
    }
  }, [])

  return {
    isConnected,
    sendMessage,
    messages,
    username,
    register,
  }
}
