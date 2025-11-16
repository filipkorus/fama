import React, { useEffect, useRef, useState } from 'react'
import {
  Box,
  Paper,
  List,
  ListItem,
  ListItemAvatar,
  Avatar,
  ListItemText,
  TextField,
  IconButton,
  Typography,
  Divider,
  Chip,
  Stack,
  InputAdornment,
  Fade,
} from '@mui/material'
import AttachFileIcon from '@mui/icons-material/AttachFile'
import SendIcon from '@mui/icons-material/Send'
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile'
import { useWebSocket } from '../hooks/useWebSocket'
import ContactList from './ContactList'

interface DisplayMessage {
  id: string
  from: string
  text: string
  to?: string
  attachments?: { name: string }[]
}

const seedMessages: DisplayMessage[] = [
  
  { id: 'm3', from: 'Server', text: 'Welcome to the demo chat. You can attach files and send messages.' },
]

interface ChatProps {
  to?: string | null
}

export const Chat: React.FC<ChatProps> = ({ to: toProp }) => {
  const { messages: wsMessages, sendMessage, username } = useWebSocket()
  const [messageInput, setMessageInput] = useState('')
  const [attachments, setAttachments] = useState<File[]>([])
  const [localMessages, setLocalMessages] = useState<DisplayMessage[]>([...seedMessages])
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const [selectedContact, setSelectedContact] = useState<string | null>(toProp || 'alice')

  const handleSend = () => {
    const names = attachments.map((f) => f.name)
    let composed = messageInput.trim()
    if (!composed && names.length === 0) return

    if (names.length > 0) {
      composed = `${composed} ${names.map((n) => `[attachment:${n}]`).join(' ')}`.trim()
    }

    // send via websocket hook (to for one-to-one)
    sendMessage(composed, selectedContact || undefined)

    // Optimistic UI update
    setLocalMessages((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        from: username || 'me',
        to: selectedContact || undefined,
        text: composed || '(attachment)',
        attachments: attachments.map((f) => ({ name: f.name })),
      },
    ])

    setMessageInput('')
    setAttachments([])
  }

  // Merge websocket messages (simple string) into display messages
  useEffect(() => {
    if (!wsMessages || wsMessages.length === 0) return
    // Try to parse messages as objects if possible
    const newItems = wsMessages.slice(-5).map((m, idx) => {
      try {
        const obj = typeof m === 'string' ? JSON.parse(m) : m
        if (obj && typeof obj === 'object' && obj.message) {
          return {
            id: `ws-${Date.now()}-${idx}`,
            from: obj.from || 'Server',
            to: obj.to || undefined,
            text: obj.message,
          }
        }
      } catch {
        // fallback to string parsing
      }
      // fallback: treat as string
      return {
        id: `ws-${Date.now()}-${idx}`,
        from: m.startsWith('You:') ? (username || 'me') : m.split(':')[0] || 'Server',
        to: undefined,
        text: m,
      }
    })
    setLocalMessages((prev) => {
      // Prevent duplicate dummy messages
      const hasDummies = prev.some(msg => msg.id === 'm1' || msg.id === 'm2' || msg.id === 'm3')
      const base = hasDummies ? prev : [...seedMessages, ...prev]
      return [...base, ...newItems]
    })
  }, [wsMessages, username])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [localMessages])

  const onAttachClick = () => fileInputRef.current?.click()

  const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    const files = e.target.files
    if (!files) return
    setAttachments((prev) => [...prev, ...Array.from(files)])
    e.currentTarget.value = ''
  }

  const handleRemoveAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index))
  }

  // Filter messages for one-to-one chat
  const filteredMessages = selectedContact
    ? [
        // Show relevant dummy messages for the selected contact
        ...seedMessages.filter(
          (m) =>
            ((m.from === username || m.from === 'me') && m.to === selectedContact) ||
            (m.from === selectedContact && (m.to === username || m.to === 'me')) ||
            (m.from === 'Server' && (!m.to || m.to === username || m.to === 'me'))
        ),
        // Then show real messages, but skip duplicates
        ...localMessages.filter(
          (m) =>
            ((m.from === username || m.from === 'me') && m.to === selectedContact) ||
            (m.from === selectedContact && (m.to === username || m.to === 'me')) ||
            (!m.to && (m.from === selectedContact || m.from === username || m.from === 'me'))
        ).filter((m) => !seedMessages.some((d) => d.id === m.id)),
      ]
    : [...seedMessages, ...localMessages.filter((m) => !seedMessages.some((d) => d.id === m.id))]

  return (
    <Fade in>
      <Box>
        <Paper
          elevation={8}
          sx={{
            display: 'flex',
            flexDirection: 'row',
            width: '100%',
            maxWidth: 900,
            mx: 'auto',
            bgcolor: 'rgba(20,0,30,0.95)',
            borderRadius: 4,
            boxShadow: '0 0 40px #a020f0',
            color: '#fff',
            fontFamily: 'inherit',
            overflow: 'hidden',
          }}
        >
          <Box sx={{ width: 260, minWidth: 220, maxWidth: 280, bgcolor: 'rgba(30,0,40,0.7)', borderRight: '2px solid #2a003f', p: 0, display: 'flex', flexDirection: 'column', justifyContent: 'stretch' }}>
            <ContactList selected={selectedContact} onSelect={setSelectedContact} noPaper />
          </Box>
          <Box sx={{ flex: 1, minWidth: 0, px: 0, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ px: 4, pt: 4, pb: 1 }}>
              <Typography
                variant="h4"
                sx={{
                  color: '#ff4fff',
                  fontWeight: 700,
                  textAlign: 'center',
                  fontFamily: 'inherit',
                  mb: 1,
                  letterSpacing: 1,
                }}
              >
                {selectedContact ? `Chat with ${selectedContact.charAt(0).toUpperCase() + selectedContact.slice(1)}` : 'Chat Room'}
              </Typography>
              <Divider sx={{ bgcolor: '#a020f0', mb: 2 }} />
            </Box>

            <Box
              ref={scrollRef}
              sx={{
                maxHeight: '45vh',
                overflowY: 'auto',
                px: 3,
                pb: 2,
                bgcolor: 'transparent',
              }}
            >
              <List>
                {filteredMessages.map((m) => (
                  <ListItem
                    key={m.id}
                    alignItems="flex-start"
                    sx={{
                      py: 1,
                      bgcolor:
                        m.from === username
                          ? 'rgba(160,32,240,0.10)'
                          : 'rgba(255,79,255,0.05)',
                      borderRadius: 2,
                      mb: 1,
                      boxShadow:
                        m.from === username
                          ? '0 0 10px #a020f0'
                          : '0 0 6px #ff4fff',
                    }}
                  >
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: m.from === username ? '#a020f0' : '#ff4fff', color: '#fff' }}>
                        {m.from ? m.from.charAt(0).toUpperCase() : 'S'}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                          <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 600 }}>
                            {m.from}
                          </Typography>
                          <Typography variant="body2" sx={{ color: '#ffbfff', fontWeight: 400 }}>
                            {m.text}
                          </Typography>
                        </Box>
                      }
                      secondary={
                        m.attachments && m.attachments.length > 0 ? (
                          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                            {m.attachments.map((a, i) => (
                              <Chip
                                key={i}
                                icon={<InsertDriveFileIcon fontSize="small" />}
                                label={a.name}
                                size="small"
                                sx={{ bgcolor: '#a020f0', color: '#fff' }}
                              />
                            ))}
                          </Stack>
                        ) : null
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Box>

            <Divider sx={{ bgcolor: '#a020f0', my: 1 }} />

            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end', px: 3, pb: 3 }}>
              <TextField
                fullWidth
                multiline
                maxRows={4}
                placeholder="Type a message..."
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                sx={{
                  bgcolor: 'rgba(30,0,40,0.8)',
                  borderRadius: 2,
                  input: { color: '#fff' },
                  textarea: { color: '#fff' },
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: '#a020f0',
                  },
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: '#ff4fff',
                  },
                }}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={onAttachClick} edge="end" aria-label="attach" sx={{ color: '#ff4fff' }}>
                        <AttachFileIcon />
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <IconButton color="primary" onClick={handleSend} aria-label="send" sx={{ bgcolor: '#a020f0', color: '#fff', '&:hover': { bgcolor: '#ff4fff' } }}>
                <SendIcon />
              </IconButton>
            </Box>

            {attachments.length > 0 && (
              <Box sx={{ px: 3, pb: 2 }}>
                <Stack direction="row" spacing={1}>
                  {attachments.map((f, i) => (
                    <Chip
                      key={i}
                      icon={<InsertDriveFileIcon />}
                      label={f.name}
                      onDelete={() => handleRemoveAttachment(i)}
                      sx={{ bgcolor: '#a020f0', color: '#fff' }}
                    />
                  ))}
                </Stack>
              </Box>
            )}

            <input ref={fileInputRef} type="file" style={{ display: 'none' }} multiple onChange={handleFileChange} />
          </Box>
        </Paper>
      </Box>
    </Fade>
  )
}

export default Chat
