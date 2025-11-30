import React, { useEffect, useRef, useState, useLayoutEffect } from "react";
import { Box, Paper, Fade, CircularProgress, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useWebSocket, MessageData } from "../hooks/useWebSocket";
import { logout } from "../services/auth";
import ContactList from "./ContactList";
import ChatHeader from "./ChatHeader";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";

interface DisplayMessage {
  id: string;
  from: string;
  text: string;
  to?: string;
  attachments?: { name: string }[];
}

interface ChatProps {
  to?: string | null;
}

export const Chat: React.FC<ChatProps> = ({ to: toProp }) => {
  const navigate = useNavigate();
  const {
    messagesByUser,
    username,
    isConnected,
    recentUsers,
    availableUsers,
    isUsersLoaded, 
    sendMessage,
    loadMessagesHistory,
  } = useWebSocket();

  const [messageInput, setMessageInput] = useState("");
  const [attachments, setAttachments] = useState<File[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  
  const prevScrollHeightRef = useRef<number>(0);
  const lastMessageCountRef = useRef<number>(0);

  const allUsers = [...recentUsers, ...availableUsers];
  
  const targetUser = isUsersLoaded ? allUsers.find((u) => u.username === toProp) : null;
  const targetUserId = targetUser?.id;

  const currentMessages = targetUserId ? messagesByUser[String(targetUserId)] || [] : [];

  useEffect(() => {
    if (!isConnected || !isUsersLoaded) return;
    if (allUsers.length === 0) return;

    const userExists = allUsers.some(u => u.username === toProp);

    if (!toProp || !userExists) {
      const firstUser = allUsers[0];
      if (firstUser) {
        navigate(`/chat/${firstUser.username}`, { replace: true });
      }
    }
  }, [toProp, isConnected, isUsersLoaded, allUsers, navigate]);

  useEffect(() => {
    if (targetUserId) {
      lastMessageCountRef.current = 0;
      setLoadingHistory(false);
      
      if (currentMessages.length === 0) {
        loadMessagesHistory(targetUserId, 0);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetUserId]); 

  useLayoutEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const currentCount = currentMessages.length;
    const previousCount = lastMessageCountRef.current;
    if (currentCount === previousCount) return;

    if (loadingHistory) {
      const newScrollHeight = container.scrollHeight;
      const heightDifference = newScrollHeight - prevScrollHeightRef.current;
      
      container.scrollTop = heightDifference;
      
      setLoadingHistory(false);
    } else {
      
      container.scrollTop = container.scrollHeight;
    }

    lastMessageCountRef.current = currentCount;

  }, [currentMessages, loadingHistory]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget;

    if (container.scrollTop === 0 && !loadingHistory && currentMessages.length > 0) {
      console.log("[Chat] Scrolled to top, loading more history...");
      
      setLoadingHistory(true);
      
      prevScrollHeightRef.current = container.scrollHeight;

      if (targetUserId) {
        loadMessagesHistory(targetUserId, currentMessages.length);
      }
    }
  };

  const handleSend = async () => {
    let composed = messageInput.trim();
    if (!targetUser || !targetUserId || !targetUser.public_key) return;

    try {
      setLoadingHistory(false); 
      await sendMessage(composed, targetUserId, targetUser.public_key);
      setMessageInput("");
      setAttachments([]);
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const transformMessages = (messages: MessageData[]): DisplayMessage[] => {
    return messages.map((msg) => ({
      id: String(msg.id),
      from: msg.from || "Unknown",
      text: msg.message || "",
      to: msg.to,
      timestamp: msg.timestamp
    }));
  };

  if (!isUsersLoaded) {
    return (
      <Box sx={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', bgcolor: "#1a002a", flexDirection: 'column', gap: 2 }}>
        <CircularProgress color="secondary" />
        <Typography sx={{ color: '#fff' }}>Ładowanie kontaktów...</Typography>
      </Box>
    );
  }

  if (allUsers.length === 0) {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
        <ChatHeader username={username} isConnected={isConnected} onLogout={() => { logout(); navigate("/"); }} />
        <Box sx={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', bgcolor: "#1a002a", color: '#fff', flexDirection: 'column' }}>
          <Typography variant="h5" gutterBottom>Brak dostępnych użytkowników</Typography>
          <Typography variant="body1">Nie znaleziono nikogo online ani w historii.</Typography>
        </Box>
      </Box>
    );
  }

  if (!targetUser) {
    return (
       <Box sx={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', bgcolor: "#1a002a" }}>
        <CircularProgress color="secondary" />
      </Box>
    );
  }

  return (
    <Fade in>
      <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
        <ChatHeader
          username={username}
          isConnected={isConnected}
          onLogout={() => {
            logout();
            navigate("/");
          }}
        />
        <Paper
          elevation={8}
          sx={{
            display: "flex",
            flexDirection: "row",
            width: "100%",
            maxWidth: 1000,
            mx: "auto",
            my: 2,
            bgcolor: "rgba(20,0,30,0.95)",
            borderRadius: 4,
            boxShadow: "0 0 40px #a020f0",
            color: "#fff",
            fontFamily: "inherit",
            overflow: "hidden",
            flex: 1,
          }}
        >
          <Box
            sx={{
              width: 280,
              bgcolor: "rgba(30,0,40,0.7)",
              borderRight: "2px solid #2a003f",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <ContactList 
                selected={toProp || ""} 
                recentUsers={recentUsers}
                availableUsers={availableUsers}
                messagesByUser={messagesByUser}
                noPaper 
            />
          </Box>

          <Box
            sx={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              minWidth: 0,
            }}
          >
            <Box 
                ref={scrollRef}
                onScroll={handleScroll}
                sx={{ 
                    flex: 1, 
                    overflowY: "auto", 
                    display: "flex", 
                    flexDirection: "column",
                    p: 2,
                    "&::-webkit-scrollbar": { width: "8px" },
                    "&::-webkit-scrollbar-thumb": { backgroundColor: "#a020f0", borderRadius: "4px" }
                }}
            >
                <MessageList
                  messages={transformMessages(currentMessages)}
                  username={username}
                />
            </Box>

            <MessageInput
              messageInput={messageInput}
              setMessageInput={setMessageInput}
              attachments={attachments}
              setAttachments={setAttachments}
              onSend={handleSend}
              fileInputRef={fileInputRef}
              disabled={!isConnected}
            />
          </Box>
        </Paper>
      </Box>
    </Fade>
  );
};

export default Chat;
