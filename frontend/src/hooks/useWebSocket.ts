import { useState, useEffect, useCallback } from 'react'
import { socket } from '../services/socket'
import { decryptMessage } from '../services/message' 
import User from '../types/User'

interface EncryptedMessagePayload {
  id: number
  sender: {
    id: number
    username: string
  }
  encrypted_content: string
  capsule_mlkem: string
  nonce: string
  is_delivered: boolean
  created_at: string
}

// Ujednolicony format wiadomości w stanie aplikacji
export interface MessageData {
  id?: string | number
  from?: string
  message?: string
  to?: string
  timestamp?: string
  attachments?: any[]
}



interface UseWebSocketReturn {
  isConnected: boolean
  sendMessage: (message: string, to?: string) => void
  messages: (string | MessageData)[]
  username: string | null
  register: (username: string) => void
  recentUsers: User[]
  availableUsers: User[]
  loadUsers: () => void
  loadMessagesHistory: (recipientId: number | string, limit?: number, offset?: number) => void
  socket: typeof socket
}

export const useWebSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<(string | MessageData)[]>([])
  const [username, setUsername] = useState<string | null>(null)
  const [recentUsers, setRecentUsers] = useState<User[]>([])
  const [availableUsers, setAvailableUsers] = useState<User[]>([])

  const loadUsers = useCallback(() => {
    if (!socket) return;
    socket.emit('get_recent_and_available_users', {})
  }, [])

  const loadMessagesHistory = useCallback((recipientId: number | string, limit = 50, offset = 0) => {
    if (!socket || !recipientId) return;

    setMessages([]); 

    console.log(`Requesting history for ${recipientId}`);
    socket.emit('get_messages', {
      recipient_id: recipientId,
      limit: limit,
      offset: offset
    });
  }, []);

  useEffect(() => {
    const onConnect = () => {
      setIsConnected(true)
      console.log('Connected to WebSocket server')
    }

    const onDisconnect = () => {
      setIsConnected(false)
      console.log('Disconnected from server')
    }

    // 1. Obsługa zwykłych wiadomości tekstowych (Legacy/Broadcast)
    const onMessage = (data: string | MessageData) => {
      if (typeof data === 'string') {
        setMessages((prev) => [...prev, data])
      } else if (data && typeof data === 'object') {
        const msgObj: MessageData = {
          from: data.from || 'Server',
          message: data.message || '',
          to: data.to,
          id: `legacy-${Date.now()}-${Math.random()}`
        }
        setMessages((prev) => [...prev, msgObj])
      }
    }

    // 2. Obsługa NOWYCH wiadomości zaszyfrowanych (Live)
    const onReceiveMessage = async (payload: EncryptedMessagePayload) => {
      console.log('Received encrypted message (Live):', payload.id)
      
      try {
        // Używamy Twojej funkcji decryptMessage z messages.ts
        const plainText = await decryptMessage(
          payload.capsule_mlkem,
          payload.encrypted_content,
          payload.nonce
        )

        const newMessage: MessageData = {
          id: payload.id,
          from: payload.sender.username,
          message: plainText,
          timestamp: payload.created_at,
        }

        setMessages((prev) => [...prev, newMessage])
        loadUsers() // Odśwież listę, aby przesunąć użytkownika na górę
        
      } catch (error) {
        console.error('Failed to decrypt live message:', error)
        setMessages((prev) => [...prev, {
            id: payload.id,
            from: payload.sender.username,
            message: '⚠️ Error: Decryption Failed',
            type: 'private'
        }])
      }
    }

    // 3. Obsługa HISTORII wiadomości (History)
    const onMessagesHistory = async (data: any) => {
      console.log("History received, processing...", data);
      
      const rawMessages = Array.isArray(data) ? data : (data.messages || []);
      if (!Array.isArray(rawMessages)) return;

      // Przetwarzamy całą tablicę równolegle
      const processedHistory = await Promise.all(
        rawMessages.map(async (msg: any) => {
          // A. Jeśli wiadomość jest zaszyfrowana
          if (msg.encrypted_content && msg.capsule_mlkem && msg.nonce) {
            try {
              const plainText = await decryptMessage(
                msg.capsule_mlkem,
                msg.encrypted_content,
                msg.nonce
              );
              
              return {
                id: msg.id,
                from: msg.sender?.username || 'Unknown',
                message: plainText,
                timestamp: msg.created_at,
                type: 'private'
              } as MessageData;
            } catch (err) {
              console.error(`Failed to decrypt history msg ${msg.id}`, err);
              return {
                id: msg.id,
                from: msg.sender?.username || 'Unknown',
                message: '⚠️ Decryption Error',
                timestamp: msg.created_at,
                type: 'private'
              } as MessageData;
            }
          }
          return {
                id: 'n/a',
                from: 'n/a',
                message: 'n/a',
                timestamp: new Date().toISOString(),
                type: 'private'
              } as MessageData;
      })
      );

      setMessages(processedHistory);
    };

    const onRegistered = (data: any) => {
      setUsername(data.username)
      console.log('Registered as:', data.username)
    }

    const onRecentAndAvailableUsers = (data: unknown) => {
      if (typeof data === 'object' && data !== null && 'recent_users' in data) setRecentUsers((data as any).recent_users)
      if (typeof data === 'object' && data !== null && 'available_users' in data) setAvailableUsers((data as any).available_users)
    }

    // Rejestracja listenerów
    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('message', onMessage)
    socket.on('receive_message', onReceiveMessage)
    socket.on('registered', onRegistered)
    socket.on('recent_and_available_users', onRecentAndAvailableUsers)
    socket.on('messages_history', onMessagesHistory)

    if (socket.connected) setIsConnected(true)

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('message', onMessage)
      socket.off('receive_message', onReceiveMessage)
      socket.off('registered', onRegistered)
      socket.off('recent_and_available_users', onRecentAndAvailableUsers)
      socket.off('messages_history', onMessagesHistory)
    }
  }, [loadUsers]) // Usunięto decryptMessage z zależności, bo jest importowany statycznie

  const register = useCallback((username: string) => {
    socket.emit('register', { username })
  }, [])

  const sendMessage = useCallback((message: string, to?: string) => {
    if (!message.trim()) return
    if (to) {
      socket.emit('message', { message, to })
    } else {
      socket.emit('message', { message })
    }
  }, [])

  return {
    isConnected,
    sendMessage,
    messages,
    username,
    register,
    recentUsers,
    availableUsers,
    loadUsers,
    loadMessagesHistory,
    socket,
  }
}
