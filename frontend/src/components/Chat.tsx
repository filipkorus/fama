import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
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
} from "@mui/material";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import SendIcon from "@mui/icons-material/Send";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import { useWebSocket } from "../hooks/useWebSocket";
import { logout } from "../services/auth";
import { sendEncryptedMessage, preloadPublicKey, getUserIdByUsername } from "../services/message";
import ContactList from "./ContactList";

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
    messages: wsMessages,
    username,
    isConnected,
    recentUsers,
    availableUsers,
    socket,
    loadMessagesHistory,
  } = useWebSocket();
  const [messageInput, setMessageInput] = useState("");
  const [attachments, setAttachments] = useState<File[]>([]);
  const [localMessages, setLocalMessages] = useState<DisplayMessage[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const selectedContact = toProp || "unknown";
  


  useEffect(() => {
    const allUsers = [...recentUsers, ...availableUsers];
    const contactId = getUserIdByUsername(selectedContact, allUsers);
    if (contactId !== null) loadMessagesHistory(contactId);
    
  }, [selectedContact, loadMessagesHistory]);

  
  useEffect(() => {
    if (wsMessages.length < processedCountRef.current) {
      processedCountRef.current = 0;
    }

    if (wsMessages.length === processedCountRef.current) return;

    const newIncomingMessages = wsMessages.slice(processedCountRef.current);

    processedCountRef.current = wsMessages.length;

    const newDisplayMessages = newIncomingMessages.map((m, idx) => {
      const uniqueSuffix = `${Date.now()}-${idx}`;

      if (typeof m === "object" && m !== null) {
        const msgId = m.id ? String(m.id) : `ws-obj-${uniqueSuffix}`;
        return {
          id: msgId,
          from: m.from || "Server",
          to: m.to || undefined,
          text: m.message || "",
          attachments: [],
        };
      }

      // Case B: Legacy JSON String (e.g. { "message": "hi" })
      try {
        const obj = typeof m === "string" ? JSON.parse(m) : m;
        if (obj && typeof obj === "object" && obj.message) {
          return {
            id: `ws-json-${uniqueSuffix}`,
            from: obj.from || "Server",
            to: obj.to || undefined,
            text: obj.message,
            attachments: [],
          };
        }
      } catch {
        // ignore parse errors
      }

      // Case C: Raw String (e.g. "Welcome!")
      return {
        id: `ws-str-${uniqueSuffix}`,
        from:
          typeof m === "string" && m.startsWith("You:")
            ? username || "me"
            : typeof m === "string"
            ? m.split(":")[0]
            : "Server",
        to: undefined,
        text: typeof m === "string" ? m : JSON.stringify(m),
        attachments: [],
      };
    });

    // 5. Update state by appending ONLY these new valid messages
    setLocalMessages((prev) => {
      // Double-check: ensure we don't accidentally add an ID that already exists
      const existingIds = new Set(prev.map((p) => p.id));
      const trulyUnique = newDisplayMessages.filter(
        (m) => !existingIds.has(m.id)
      );

      if (trulyUnique.length === 0) return prev;

      return [...prev, ...trulyUnique];
    });
  }, [wsMessages, username]);

  // Validate if contact exists, redirect to most recent if not
  useEffect(() => {
    const allUsers = [...recentUsers, ...availableUsers];
    const contactExists = allUsers.some((u) => u.username === toProp);

    if (!contactExists && allUsers.length > 0) {
      // Redirect to most recent user
      navigate(`/chat/${allUsers[0].username}`);
    }
  }, [toProp, recentUsers, availableUsers, navigate]);

  // Preload public key when entering chat with a user
  useEffect(() => {
    if (toProp && toProp !== "unknown") {
      preloadPublicKey(toProp).catch((error) => {
        console.error(`Failed to preload public key for ${toProp}:`, error);
      });
    }
  }, [toProp]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleSend = async () => {
    const names = attachments.map((f) => f.name);
    let composed = messageInput.trim();
    if (!composed && names.length === 0) return;

    if (names.length > 0) {
      composed = `${composed} ${names
        .map((n) => `[attachment:${n}]`)
        .join(" ")}`.trim();
    }

    try {
      // Send encrypted message
      await sendEncryptedMessage(socket, selectedContact, composed);

      // Optimistic UI update
      setLocalMessages((prev) => [
        ...prev,
        {
          id: `local-${Date.now()}`,
          from: username || "me",
          to: selectedContact || undefined,
          text: composed || "(attachment)",
          attachments: attachments.map((f) => ({ name: f.name })),
        },
      ]);

      setMessageInput("");
      setAttachments([]);
    } catch (error) {
      console.error("Failed to send message:", error);
      // Show error to user
    }
  };

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [localMessages]);

  const onAttachClick = () => fileInputRef.current?.click();

  const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    const files = e.target.files;
    if (!files) return;
    setAttachments((prev) => [...prev, ...Array.from(files)]);
    e.currentTarget.value = "";
  };

  const handleRemoveAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <Fade in>
      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "10px 20px",
            backgroundColor: "rgba(20, 0, 30, 0.95)",
            borderBottom: "1px solid #a020f0",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <span
              style={{ color: "#ff4fff", fontWeight: "bold", fontSize: "18px" }}
            >
              FAMA
            </span>
            <span style={{ color: "#999", fontSize: "12px" }}>
              – secure chat
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
            {username && (
              <div style={{ fontSize: "14px", color: "#999" }}>
                Logged in as: <strong>{username}</strong>
              </div>
            )}
            <div
              style={{
                padding: "8px 12px",
                borderRadius: "4px",
                backgroundColor: isConnected ? "#228B22" : "#DC143C",
                color: "white",
                fontSize: "14px",
                fontWeight: "bold",
              }}
            >
              {isConnected ? "🟢 Connected" : "🔴 Disconnected"}
            </div>
            <button
              onClick={handleLogout}
              style={{
                padding: "8px 16px",
                backgroundColor: "#ff4444",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                fontSize: "14px",
              }}
            >
              Logout
            </button>
          </div>
        </header>
        <Paper
          elevation={8}
          sx={{
            display: "flex",
            flexDirection: "row",
            width: "100%",
            maxWidth: 900,
            mx: "auto",
            bgcolor: "rgba(20,0,30,0.95)",
            borderRadius: 4,
            boxShadow: "0 0 40px #a020f0",
            color: "#fff",
            fontFamily: "inherit",
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              width: 260,
              minWidth: 220,
              maxWidth: 280,
              bgcolor: "rgba(30,0,40,0.7)",
              borderRight: "2px solid #2a003f",
              p: 0,
              display: "flex",
              flexDirection: "column",
              justifyContent: "stretch",
            }}
          >
            <ContactList selected={selectedContact} noPaper />
          </Box>
          <Box
            sx={{
              flex: 1,
              minWidth: 0,
              px: 0,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Box sx={{ px: 4, pt: 4, pb: 1 }}>
              <Typography
                variant="h4"
                sx={{
                  color: "#ff4fff",
                  fontWeight: 700,
                  textAlign: "center",
                  fontFamily: "inherit",
                  mb: 1,
                  letterSpacing: 1,
                }}
              >
                {selectedContact ? `Chat with ${selectedContact}` : "Chat Room"}
              </Typography>
              <Divider sx={{ bgcolor: "#a020f0", mb: 2 }} />
            </Box>

            <Box
              ref={scrollRef}
              sx={{
                maxHeight: "45vh",
                overflowY: "auto",
                px: 3,
                pb: 2,
                bgcolor: "transparent",
              }}
            >
              {localMessages.length === 0 ? (
                "Welcome to the demo chat. You can attach files and send messages."
              ) : (
                <List>
                  {localMessages.map((m) => (
                    <ListItem
                      key={m.id}
                      alignItems="flex-start"
                      sx={{
                        py: 1,
                        bgcolor:
                          m.from === username
                            ? "rgba(160,32,240,0.10)"
                            : "rgba(255,79,255,0.05)",
                        borderRadius: 2,
                        mb: 1,
                        boxShadow:
                          m.from === username
                            ? "0 0 10px #a020f0"
                            : "0 0 6px #ff4fff",
                      }}
                    >
                      <ListItemAvatar>
                        <Avatar
                          sx={{
                            bgcolor:
                              m.from === username ? "#a020f0" : "#ff4fff",
                            color: "#fff",
                          }}
                        >
                          {m.from ? m.from.charAt(0).toUpperCase() : "S"}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Box
                            sx={{
                              display: "flex",
                              gap: 1,
                              alignItems: "center",
                            }}
                          >
                            <Typography
                              variant="subtitle2"
                              sx={{ color: "#fff", fontWeight: 600 }}
                            >
                              {m.from}
                            </Typography>
                            <Typography
                              variant="body2"
                              sx={{ color: "#ffbfff", fontWeight: 400 }}
                            >
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
                                  icon={
                                    <InsertDriveFileIcon fontSize="small" />
                                  }
                                  label={a.name}
                                  size="small"
                                  sx={{ bgcolor: "#a020f0", color: "#fff" }}
                                />
                              ))}
                            </Stack>
                          ) : null
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>

            <Divider sx={{ bgcolor: "#a020f0", my: 1 }} />

            <Box
              sx={{
                display: "flex",
                gap: 1,
                alignItems: "flex-end",
                px: 3,
                pb: 3,
              }}
            >
              <TextField
                fullWidth
                multiline
                maxRows={4}
                placeholder="Type a message..."
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                sx={{
                  bgcolor: "rgba(30,0,40,0.8)",
                  borderRadius: 2,
                  input: { color: "#fff" },
                  textarea: { color: "#fff" },
                  "& .MuiOutlinedInput-notchedOutline": {
                    borderColor: "#a020f0",
                  },
                  "&:hover .MuiOutlinedInput-notchedOutline": {
                    borderColor: "#ff4fff",
                  },
                }}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={onAttachClick}
                        edge="end"
                        aria-label="attach"
                        sx={{ color: "#ff4fff" }}
                      >
                        <AttachFileIcon />
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <IconButton
                color="primary"
                onClick={handleSend}
                aria-label="send"
                sx={{
                  bgcolor: "#a020f0",
                  color: "#fff",
                  "&:hover": { bgcolor: "#ff4fff" },
                }}
              >
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
                      sx={{ bgcolor: "#a020f0", color: "#fff" }}
                    />
                  ))}
                </Stack>
              </Box>
            )}

            <input
              ref={fileInputRef}
              type="file"
              style={{ display: "none" }}
              multiple
              onChange={handleFileChange}
            />
          </Box>
        </Paper>
      </Box>
    </Fade>
  );
};

export default Chat;