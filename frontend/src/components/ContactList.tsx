import React from 'react';
import { 
  List, 
  ListItemButton, 
  ListItemText, 
  ListItemAvatar, 
  Avatar, 
  Typography, 
  Box, 
  Divider,
  ListSubheader
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import PersonIcon from '@mui/icons-material/Person';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import User from '../types/User';
import { MessageData } from '../hooks/useWebSocket';
import { formatTimeAgo } from '../utils/date';

interface ContactListProps {
  selected: string;
  recentUsers: User[];
  availableUsers: User[];
  messagesByUser: Record<string, MessageData[]>;
  noPaper?: boolean;
}

const ContactList: React.FC<ContactListProps> = ({ 
  selected, 
  recentUsers, 
  availableUsers, 
  messagesByUser, 
}) => {
  const navigate = useNavigate();

  const handleSelect = (username: string) => {
    navigate(`/chat/${username}`);
  };

  const renderUserItem = (user: User, isRecent: boolean) => {
    const isSelected = selected === user.username;
    
    const userMessages = messagesByUser[String(user.id)] || [];
    const lastLocalMessage = userMessages.length > 0 ? userMessages[userMessages.length - 1] : null;
    
    let snippet = "";
    let timeToDisplay = null;

    if (isRecent) {
        if (lastLocalMessage) {
            snippet = lastLocalMessage.message || "Sent an attachment";
            timeToDisplay = lastLocalMessage.timestamp;
        } else {
            snippet = "History available";
            timeToDisplay = user.last_message_date;
        }
    } else {
        snippet = "Tap to start chatting";
        timeToDisplay = null;
    }

    if (snippet.length > 30) snippet = snippet.substring(0, 30) + "...";

    const timeAgo = formatTimeAgo(timeToDisplay);

    return (
      <ListItemButton
        key={user.id}
        selected={isSelected}
        onClick={() => handleSelect(user.username)}
        sx={{
          borderRadius: 2,
          mb: 0.5,
          mx: 1,
          transition: 'all 0.2s',
          borderLeft: isSelected ? "4px solid #a020f0" : "4px solid transparent",
          bgcolor: isSelected ? "rgba(160, 32, 240, 0.15)" : "transparent",
          "&:hover": {
            bgcolor: isSelected ? "rgba(160, 32, 240, 0.25)" : "rgba(255, 255, 255, 0.05)",
          },
        }}
      >
        <ListItemAvatar>
          <Avatar 
            sx={{ 
                bgcolor: isSelected ? "#a020f0" : (isRecent ? "#555" : "transparent"),
                color: "#fff",
                border: isRecent ? 'none' : '1px solid rgba(255,255,255,0.2)'
            }}
          >
            {isRecent ? (
                user.username.charAt(0).toUpperCase()
            ) : (
                <PersonIcon sx={{ opacity: 0.7 }} />
            )}
          </Avatar>
        </ListItemAvatar>
        
        <ListItemText
          primary={
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography 
                    variant="body1" 
                    component="span" 
                    sx={{ 
                        fontWeight: isSelected || isRecent ? 600 : 400, 
                        color: '#fff' 
                    }}
                >
                    {user.username}
                </Typography>
                {isRecent && timeAgo && (
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                        {timeAgo}
                    </Typography>
                )}
            </Box>
          }
          secondary={
            <Typography 
                variant="body2" 
                sx={{ 
                    color: isSelected ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.4)',
                    fontSize: '0.8rem',
                    fontStyle: !isRecent ? 'italic' : 'normal'
                }}
            >
                {snippet}
            </Typography>
          }
        />
      </ListItemButton>
    );
  };

  return (
    <List 
        sx={{ 
            width: '100%', 
            height: '100%', 
            overflowY: 'auto', 
            py: 1,
            "&::-webkit-scrollbar": { width: "6px" },
            "&::-webkit-scrollbar-thumb": { backgroundColor: "rgba(255,255,255,0.2)", borderRadius: "3px" }
        }}
    >
      {recentUsers.length > 0 && (
        <>
          <ListSubheader sx={{ bgcolor: 'transparent', color: '#a020f0', fontWeight: 'bold', fontSize: '0.75rem', lineHeight: '30px' }}>
            RECENT CHATS
          </ListSubheader>
          {recentUsers.map(u => renderUserItem(u, true))}
        </>
      )}

      {availableUsers.length > 0 && (
        <>
           {recentUsers.length > 0 && <Divider sx={{ my: 1, borderColor: 'rgba(255,255,255,0.1)' }} />}
           <ListSubheader sx={{ bgcolor: 'transparent', color: 'rgba(255,255,255,0.5)', fontWeight: 'bold', fontSize: '0.75rem', lineHeight: '30px' }}>
            AVAILABLE CONTACTS
          </ListSubheader>
          {availableUsers.map(u => renderUserItem(u, false))}
        </>
      )}

      {recentUsers.length === 0 && availableUsers.length === 0 && (
        <Box sx={{ p: 4, textAlign: 'center', color: 'rgba(255,255,255,0.3)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
            <ChatBubbleOutlineIcon sx={{ fontSize: 40, opacity: 0.5 }} />
            <Typography variant="body2">No contacts found</Typography>
        </Box>
      )}
    </List>
  );
};

export default ContactList;
