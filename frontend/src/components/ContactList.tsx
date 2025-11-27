import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, List, ListItemButton, ListItemAvatar, Avatar, ListItemText, Typography, Paper } from '@mui/material'
import { useWebSocket } from '../hooks/useWebSocket'

interface Contact {
  id: string | number
  username?: string
  name?: string
}

interface ContactListProps {
  selected: string | null
  noPaper?: boolean
}

export const ContactList: React.FC<ContactListProps> = ({ selected, noPaper }) => {
  const navigate = useNavigate()
  const { recentUsers, availableUsers, loadUsers } = useWebSocket()

  // Load users on component mount only (empty dependency array)
  useEffect(() => {
    if(availableUsers.length === 0 && recentUsers.length === 0) {

      loadUsers()
      
    }
  }, [availableUsers, recentUsers])

  // Combine recent and available users, remove duplicates
  const allUsers: Contact[] = [
    ...recentUsers.map((u) => ({ id: u.username, username: u.username, name: u.username })),
    ...availableUsers
      .filter((u) => !recentUsers.some((r) => r.username === u.username))
      .map((u) => ({ id: u.username, username: u.username, name: u.username })),
  ]

  const content = (
    <Box sx={{ width: '100%', p: 2 }}>
      <Typography variant="h6" sx={{ color: '#ff4fff', fontWeight: 700, textAlign: 'center', mb: 2, fontFamily: 'inherit' }}>Contacts</Typography>
      <List>
        {allUsers.length > 0 ? (
          allUsers.map((c) => (
            <ListItemButton
              key={c.id}
              selected={selected === c.id}
              onClick={() => navigate(`/chat/${c.id}`)}
              sx={{
                borderRadius: 2,
                mb: 1,
                bgcolor: selected === c.id ? 'rgba(160,32,240,0.2)' : 'transparent',
                '&:hover': { bgcolor: 'rgba(160,32,240,0.1)' },
              }}
            >
              <ListItemAvatar>
                <Avatar sx={{ bgcolor: '#a020f0' }}>{(c.username || c.name || 'U').charAt(0).toUpperCase()}</Avatar>
              </ListItemAvatar>
              <ListItemText
                primary={<Typography sx={{ color: '#fff', fontWeight: 500 }}>{c.username || c.name || 'Unknown'}</Typography>}
              />
            </ListItemButton>
          ))
        ) : (
          <Typography sx={{ color: '#999', textAlign: 'center', py: 2 }}>No contacts available</Typography>
        )}
      </List>
    </Box>
  )
  if (noPaper) return content
  return (
    <Paper elevation={3} sx={{ width: 300, bgcolor: 'rgba(30, 0, 40, 0.7)', color: '#fff', borderRadius: 3, p: 0, boxShadow: '0 0 30px #a020f0' }}>
      {content}
    </Paper>
  )
}

export default ContactList
