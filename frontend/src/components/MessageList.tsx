import React from "react";
import {
  Box,
  List,
  ListItem,
  ListItemAvatar,
  Avatar,
  ListItemText,
  Typography,
  Stack,
  Chip,
} from "@mui/material";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import {
  downloadAndVerifyAttachment,
  FileAttachmentMetadata,
} from "../services/attachments";

interface DisplayMessage {
  id: string;
  from: string;
  text: string;
  to?: string;
  timestamp?: string | number;
  attachments?: { name: string }[];
}

interface MessageListProps {
  messages: DisplayMessage[];
  username: string | null;
}

const formatDateTime = (dateInput?: string | number) => {
  if (!dateInput) return "";

  let normalizedDate = dateInput;

  if (typeof dateInput === 'string' && !dateInput.endsWith('Z') && !/[+-]\d{2}:?\d{2}/.test(dateInput)) {
    normalizedDate = `${dateInput}Z`;
  }

  const date = new Date(normalizedDate);

  if (isNaN(date.getTime())) return "";

  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');

  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();

  return `${hours}:${minutes} ${day}.${month}.${year}`;
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  const size = bytes / Math.pow(k, i);
  const decimals = i === 0 ? 0 : (size < 10 ? 2 : 1);

  return `${size.toFixed(decimals)} ${sizes[i]}`;
};

const MessageList: React.FC<MessageListProps> = ({ messages, username }) => {
  const [verifiedIds, setVerifiedIds] = React.useState<Record<string, boolean>>(
    {}
  );

  const describeVerifyError = (err: any): string => {
    if (err && err.name === "AttachmentVerifyError") {
      const code = err.code;
      switch (code) {
        case "ENCRYPTED_HASH_MISMATCH":
          return "Załącznik został naruszony po stronie serwera (hash zaszyfrowanego pliku nie zgadza się).";
        case "DECRYPT_FAILED":
          return "Nie udało się odszyfrować załącznika (błędny klucz lub IV).";
        case "FILE_HASH_MISMATCH":
          return "Zawartość pliku różni się od oryginału (hash pliku nie zgadza się).";
        case "SIGNATURE_INVALID":
          return "Podpis kryptograficzny jest nieprawidłowy (pliku nie podpisał wskazany nadawca).";
        default:
          return "Wystąpił nieznany błąd weryfikacji załącznika.";
      }
    }
    return "Nie udało się pobrać lub zweryfikować załącznika.";
  };

  const renderMessageContent = (message: string) => {
    try {
      const parsed = JSON.parse(message);

      if (parsed && parsed.type === "file") {
        const meta = parsed as FileAttachmentMetadata;
        const key = meta.filename;
        const isVerified = !!verifiedIds[key];

        const handleClick = async (e: React.MouseEvent) => {
          e.preventDefault();
          try {
            const result = await downloadAndVerifyAttachment(meta);
            setVerifiedIds((prev) => ({ ...prev, [key]: true }));

            const url = URL.createObjectURL(result.blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
          } catch (err: any) {
            console.error("[Attachment] Failed to download/verify:", err);
            alert(describeVerifyError(err));
          }
        };

        return (
          <span onClick={handleClick} style={{ cursor: "pointer" }}>
            📎 {meta.original_filename || "Załącznik"} (
            {formatFileSize(meta.original_size || 0)})
            <br />
            {isVerified && (
              <span style={{ color: "#00ff00" }}>podpis zweryfikowany</span>
            )}
          </span>
        );
      }
    } catch {
    }

    return <>{message}</>;
  };

  return (
    <Box
      sx={{
        px: 3,
        pb: 2,
        bgcolor: "transparent",
        width: "100%"
      }}
    >
      {messages.length === 0 ? (
        <Box sx={{ p: 4, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>
          <Typography variant="body1">
            Welcome to the demo chat. You can attach files and send messages.
          </Typography>
        </Box>
      ) : (
        <List sx={{ width: '100%' }}>
          {messages.map((m) => (
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
                    bgcolor: m.from === username ? "#a020f0" : "#ff4fff",
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
                      alignItems: "baseline",
                      flexWrap: "wrap"
                    }}
                  >
                    <Typography
                      variant="subtitle2"
                      sx={{ color: "#fff", fontWeight: 600 }}
                    >
                      {m.from}
                    </Typography>
                    
                    {m.timestamp && (
                        <Typography 
                            variant="caption" 
                            sx={{ color: "rgba(255, 255, 255, 0.5)", fontSize: "0.75rem" }}
                        >
                            {formatDateTime(m.timestamp)}
                        </Typography>
                    )}

                    <Box sx={{ width: "100%", mt: 0.2 }}>
                        <Typography
                        variant="body2"
                        sx={{ color: "#ffbfff", fontWeight: 400, wordBreak: "break-word" }}
                        >
                        {renderMessageContent(m.text)}
                        </Typography>
                    </Box>
                  </Box>
                }
                secondary={
                  m.attachments && m.attachments.length > 0 ? (
                    <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap', gap: 1 }}>
                      {m.attachments.map((a, i) => (
                        <Chip
                          key={i}
                          icon={<InsertDriveFileIcon fontSize="small" />}
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
  );
};

export default MessageList;