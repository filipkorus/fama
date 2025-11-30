import { useState, useEffect, useCallback, useRef } from 'react';
import { socket } from '../services/socket';
import { 
  generateSessionKey, 
  encryptMessage, 
  decryptMessage, 
  encryptSessionKeyForRecipient, 
  decryptSessionKeyFromSender 
} from '../services/message'; 
import User from '../types/User';

interface EncryptedMessagePayload {
  id: number;
  sender: { id: number; username: string };
  recipient?: { id: number; username: string };
  recipient_id?: number;
  session_key_id: number;
  encrypted_content: string;
  nonce: string;
  is_delivered: boolean;
  created_at: string;
}

interface SessionKeyData {
  session_key_id: number;
  sender_id: number;
  capsule_mlkem: string;
  encrypted_shared_secret: string;
  key_nonce: string;
}

export interface MessageData {
  id?: string | number;
  from?: string;
  to?: string;
  message?: string;
  timestamp?: string;
  isIncoming?: boolean;
}

interface QueuedMessage {
    payload: EncryptedMessagePayload;
    partnerId?: string;
}

interface SessionKeyCache {
  [keyId: number]: string; 
}

interface ActiveSessionMap {
  [recipientId: number]: number; 
}

const STORAGE_KEYS_KEY = 'E2EE_SESSION_KEYS_V1';
const STORAGE_SESSIONS_KEY = 'E2EE_ACTIVE_SESSIONS_V1';
const HISTORY_LIMIT = 50;

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(socket.connected); 
  const [messagesByUser, setMessagesByUser] = useState<Record<string, MessageData[]>>({});
  const [username, setUsername] = useState<string | null>(null);
  const [userId, setUserId] = useState<number | null>(null);
  const [recentUsers, setRecentUsers] = useState<User[]>([]);
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);
  const [isUsersLoaded, setIsUsersLoaded] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState<Record<string, boolean>>({});

  const recentUsersRef = useRef<User[]>([]);
  const availableUsersRef = useRef<User[]>([]);

  const sessionKeys = useRef<SessionKeyCache>({});
  const activeSessions = useRef<ActiveSessionMap>({});
  const pendingDecryptionQueue = useRef<Record<number, QueuedMessage[]>>({});
  const pendingKeyPublication = useRef<Record<number, (id: number) => void>>({});

  useEffect(() => {
    try {
      const storedKeys = localStorage.getItem(STORAGE_KEYS_KEY);
      if (storedKeys) sessionKeys.current = JSON.parse(storedKeys);

      const storedSessions = localStorage.getItem(STORAGE_SESSIONS_KEY);
      if (storedSessions) {
        const parsedSessions = JSON.parse(storedSessions);
        const cleanSessions: ActiveSessionMap = {};
        Object.entries(parsedSessions).forEach(([recipId, keyId]) => {
            const kId = Number(keyId);
            if (sessionKeys.current[kId]) cleanSessions[Number(recipId)] = kId;
        });
        activeSessions.current = cleanSessions;
      }
    } catch (e) {
      console.error("[E2EE] Failed to load keys", e);
      sessionKeys.current = {};
      activeSessions.current = {};
    }
  }, []);

  const saveSessionKey = useCallback((keyId: number, aesKey: string) => {
    sessionKeys.current[keyId] = aesKey;
    localStorage.setItem(STORAGE_KEYS_KEY, JSON.stringify(sessionKeys.current));
  }, []);

  const saveActiveSession = useCallback((recipientId: number, keyId: number) => {
    activeSessions.current[recipientId] = keyId;
    localStorage.setItem(STORAGE_SESSIONS_KEY, JSON.stringify(activeSessions.current));
  }, []);

  const loadUsers = useCallback(() => {
    if (socket.connected) {
        socket.emit('get_recent_and_available_users', {});
    }
  }, []);

  const loadMessagesHistory = useCallback((recipientId: number, offset: number = 0) => {
    if (!recipientId) return;
    console.log(`[WS] Requesting history for ${recipientId}, offset: ${offset}`);
    socket.emit('get_messages', { 
        recipient_id: recipientId, 
        limit: HISTORY_LIMIT, 
        offset: offset 
    });
  }, []);

  const processMessage = useCallback(async (msg: EncryptedMessagePayload, optionalPartnerId?: string): Promise<MessageData | null> => {
    if (!msg.session_key_id) {
        console.error("[E2EE] Message missing session_key_id.", msg);
        return {
            id: msg.id,
            from: msg.sender.username,
            to: msg.recipient?.username,
            message: "⚠️ Błąd danych (brak ID klucza)",
            timestamp: msg.created_at,
            isIncoming: msg.sender.id !== userId
        };
    }

    const keyId = msg.session_key_id;
    const aesKey = sessionKeys.current[keyId];

    if (!aesKey) {
      if (!pendingDecryptionQueue.current[keyId]) {
        pendingDecryptionQueue.current[keyId] = [];
        console.log(`[E2EE] Missing Key ${keyId}. Requesting...`);
        socket.emit('request_session_key', { session_key_id: keyId });
      }
      pendingDecryptionQueue.current[keyId].push({ payload: msg, partnerId: optionalPartnerId });
      return null;
    }

    try {
      const plainText = await decryptMessage(aesKey, msg.encrypted_content, msg.nonce);
      return {
        id: msg.id,
        from: msg.sender.username,
        to: msg.recipient?.username,
        message: plainText,
        timestamp: msg.created_at,
        isIncoming: msg.sender.id !== userId
      };
    } catch (error) {
      console.error(`[E2EE] Decryption failed for msg ${msg.id}`, error);
      return {
        id: msg.id,
        from: msg.sender.username,
        to: msg.recipient?.username,
        message: '⚠️ Błąd deszyfracji',
        timestamp: msg.created_at,
        isIncoming: msg.sender.id !== userId
      };
    }
  }, [userId]);

  const flushPendingQueue = useCallback(async (keyId: number) => {
    const queue = pendingDecryptionQueue.current[keyId];
    if (!queue || queue.length === 0) return;

    console.log(`[E2EE] Flushing ${queue.length} messages for key ${keyId}`);
    
    const processedByPartner: Record<string, MessageData[]> = {};

    for (const item of queue) {
      const decrypted = await processMessage(item.payload, item.partnerId);
      if (decrypted) {
          let pId = item.partnerId;
          
          if (!pId) {
              const rawMsg = item.payload;
              if (rawMsg.sender.id === userId) {
                  pId = String(rawMsg.recipient?.id || rawMsg.recipient_id);
              } else {
                  pId = String(rawMsg.sender.id);
              }
          }

          if (pId && pId !== "undefined") {
              if (!processedByPartner[pId]) processedByPartner[pId] = [];
              processedByPartner[pId].push(decrypted);
          }
      }
    }

    setMessagesByUser((prev) => {
        const newState = { ...prev };
        Object.entries(processedByPartner).forEach(([pId, msgs]) => {
            const existing = newState[pId] || [];
            const uniqueNew = msgs.filter(m => !existing.some(ex => ex.id === m.id));
            
            if (uniqueNew.length > 0) {
                newState[pId] = [...existing, ...uniqueNew].sort((a,b) => 
                    new Date(a.timestamp!).getTime() - new Date(b.timestamp!).getTime()
                );
            }
        });
        return newState;
    });

    delete pendingDecryptionQueue.current[keyId];
  }, [processMessage, userId]);


  useEffect(() => {
    const onConnect = () => { setIsConnected(true); };
    const onDisconnect = () => setIsConnected(false);

    const onConnectedInfo = (data: { user: { id: number, username: string } }) => {
        setUserId(data.user.id);
        setUsername(data.user.username);
    };

    const onSessionKeyPublished = (data: { session_key_id: number, recipient_id: number }) => {
        if (pendingKeyPublication.current[data.recipient_id]) {
            pendingKeyPublication.current[data.recipient_id](data.session_key_id);
            delete pendingKeyPublication.current[data.recipient_id];
        }
        saveActiveSession(data.recipient_id, data.session_key_id);
    };

    const onSessionKeyData = async (data: SessionKeyData) => {
        try {
            const aesKey = await decryptSessionKeyFromSender(
                data.capsule_mlkem,
                data.encrypted_shared_secret,
                data.key_nonce
            );
            saveSessionKey(data.session_key_id, aesKey);
            if (data.sender_id !== userId) {
                 saveActiveSession(data.sender_id, data.session_key_id);
            }
            flushPendingQueue(data.session_key_id);
        } catch (err) {
            console.error("[E2EE] Failed to decrypt session key:", err);
            const keyId = data.session_key_id;
            const queue = pendingDecryptionQueue.current[keyId];
            if (queue) delete pendingDecryptionQueue.current[keyId];
        }
    };

    const onReceiveMessage = async (payload: EncryptedMessagePayload) => {
      const senderId = payload.sender.id;
      const isKnown = [
          ...recentUsersRef.current,
          ...availableUsersRef.current
      ].some(u => u.id === senderId);

      if (senderId !== userId && !isKnown) {
          console.log(`[WS] Received message from unknown user ${senderId}, reloading user lists.`);
          loadUsers();
      }

      const decryptedMsg = await processMessage(payload);
      if (decryptedMsg) {
        setMessagesByUser((prev) => {
          const senderIdStr = String(payload.sender.id);
          const current = prev[senderIdStr] || [];
          if (current.some(m => m.id === decryptedMsg.id)) return prev;
          return { ...prev, [senderIdStr]: [...current, decryptedMsg] };
        });
      }
    };

    const onMessagesHistory = async (data: { messages: EncryptedMessagePayload[], recipient_id: number }) => {
        const rawMessages = data.messages || [];
        const partnerId = String(data.recipient_id);

        const hasMore = rawMessages.length >= HISTORY_LIMIT;
        setHasMoreMessages(prev => ({ ...prev, [partnerId]: hasMore }));

        const processed = await Promise.all(rawMessages.map(msg => processMessage(msg, partnerId)));
        const validMessages = processed.filter((m): m is MessageData => m !== null);
        
        setMessagesByUser(prev => {
            const existing = prev[partnerId] || [];
            const uniqueNew = validMessages.filter(vm => !existing.some(ex => ex.id === vm.id));
            if (uniqueNew.length === 0) return prev;
            return {
                ...prev,
                [partnerId]: [...existing, ...uniqueNew].sort((a, b) => 
                    new Date(a.timestamp!).getTime() - new Date(b.timestamp!).getTime()
                )
            };
        });
    };

    const onRecentAndAvailableUsers = (data: any) => {
      const recent: any[] = data.recent_users || [];
      const available: any[] = data.available_users || [];
      
      setRecentUsers(recent);
      setAvailableUsers(available);
      
      recentUsersRef.current = recent;
      availableUsersRef.current = available;
      setIsUsersLoaded(true);
    };

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('connected', onConnectedInfo);
    socket.on('recent_and_available_users', onRecentAndAvailableUsers);
    socket.on('session_key_published', onSessionKeyPublished);
    socket.on('session_key_data', onSessionKeyData);
    socket.on('receive_message', onReceiveMessage);
    socket.on('messages_history', onMessagesHistory);

    if (socket.connected) {
      setIsConnected(true);
      if (!userId || !username) {
          socket.disconnect();
          socket.connect();
      }
    }

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('connected', onConnectedInfo);
      socket.off('session_key_published', onSessionKeyPublished);
      socket.off('session_key_data', onSessionKeyData);
      socket.off('receive_message', onReceiveMessage);
      socket.off('messages_history', onMessagesHistory);
      socket.off('recent_and_available_users', onRecentAndAvailableUsers);
    };
  }, [loadUsers, processMessage, flushPendingQueue, userId, username, saveSessionKey, saveActiveSession]);

  useEffect(() => {
    if (isConnected && !isUsersLoaded) {
        loadUsers();
    }
  }, [isConnected, isUsersLoaded, loadUsers]);


  const sendMessage = useCallback(async (text: string, recipientId: number, recipientPublicKey: string) => {
    if (!socket.connected || !username) return;
    if (!text.trim() || !recipientId) return;

    let keyId = activeSessions.current[recipientId];
    let aesKey = keyId ? sessionKeys.current[keyId] : null;

    if (!keyId || !aesKey) {
        if (!recipientPublicKey) return;
        try {
            const newAesKey = await generateSessionKey();
            const { capsule, encryptedSecret, nonce } = await encryptSessionKeyForRecipient(newAesKey, recipientPublicKey);
            
            const keyIdPromise = new Promise<number>((resolve, reject) => {
                pendingKeyPublication.current[recipientId] = resolve;
                setTimeout(() => {
                    if (pendingKeyPublication.current[recipientId]) {
                        delete pendingKeyPublication.current[recipientId];
                        reject(new Error("Timeout"));
                    }
                }, 5000);
            });
            
            socket.emit('publish_session_key', {
                recipient_id: recipientId,
                capsule_mlkem: capsule,
                encrypted_shared_secret: encryptedSecret,
                key_nonce: nonce
            });
            
            keyId = await keyIdPromise;
            saveSessionKey(keyId, newAesKey);
            saveActiveSession(recipientId, keyId);
            aesKey = newAesKey;
        } catch (e) {
            console.error(e);
            return;
        }
    }

    try {
        const { encryptedContent, nonce } = await encryptMessage(aesKey!, text);
        socket.emit('send_message', {
            recipient_id: recipientId,
            session_key_id: keyId,
            encrypted_content: encryptedContent,
            nonce: nonce
        });
        
        const optimisticMsg: MessageData = {
            id: `temp-${Date.now()}`,
            from: username,
            to: '...', 
            message: text,
            timestamp: new Date().toISOString(),
            isIncoming: false
        };
        
        setMessagesByUser(prev => {
            const key = String(recipientId);
            const existing = prev[key] || [];
            return { ...prev, [key]: [...existing, optimisticMsg] };
        });
    } catch (e) { console.error(e); }
  }, [username, saveSessionKey, saveActiveSession]);

  return { 
      isConnected, 
      sendMessage, 
      messagesByUser, 
      username, 
      userId, 
      recentUsers, 
      availableUsers, 
      isUsersLoaded, 
      loadUsers, 
      loadMessagesHistory, 
      hasMoreMessages,
      socket 
  };
};