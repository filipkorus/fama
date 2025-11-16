import React, { useState } from 'react'
import { Box, List, ListItemButton, ListItemAvatar, Avatar, ListItemText, Typography, Paper } from '@mui/material'

interface Contact {
  id: string
  name: string
}

const contacts: Contact[] = [
  { id: 'alice', name: 'Alice' },
  { id: 'bob', name: 'Bob' },
  { id: 'carol', name: 'Carol' },
  { id: 'server', name: 'Server' },
]

interface ContactListProps {
  selected: string | null
  onSelect: (id: string) => void
  noPaper?: boolean
}

export const ContactList: React.FC<ContactListProps> = ({ selected, onSelect, noPaper }) => {
  const content = (
    <Box sx={{ width: '100%', p: 2 }}>
      <Typography variant="h6" sx={{ color: '#ff4fff', fontWeight: 700, textAlign: 'center', mb: 2, fontFamily: 'inherit' }}>Contacts</Typography>
      <List>
        {contacts.map((c) => (
          <ListItemButton
            key={c.id}
            selected={selected === c.id}
            onClick={() => onSelect(c.id)}
            sx={{
              borderRadius: 2,
              mb: 1,
              bgcolor: selected === c.id ? 'rgba(160,32,240,0.2)' : 'transparent',
              '&:hover': { bgcolor: 'rgba(160,32,240,0.1)' },
            }}
          >
            <ListItemAvatar>
              <Avatar sx={{ bgcolor: '#a020f0' }}>{c.name.charAt(0).toUpperCase()}</Avatar>
            </ListItemAvatar>
            <ListItemText
              primary={<Typography sx={{ color: '#fff', fontWeight: 500 }}>{c.name}</Typography>}
            />
          </ListItemButton>
        ))}
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
