import React from "react";
import { Box, TextField, IconButton, InputAdornment, Stack, Chip } from "@mui/material";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import SendIcon from "@mui/icons-material/Send";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";

interface MessageInputProps {
  messageInput: string;
  setMessageInput: (value: string) => void;
  attachments: File[];
  setAttachments: (files: React.SetStateAction<File[]>) => void;
  onSend: () => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
  disabled?: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({
  messageInput,
  setMessageInput,
  attachments,
  setAttachments,
  onSend,
  fileInputRef,
  disabled = false,
}) => {
  const onAttachClick = () => fileInputRef.current?.click();

  const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    const files = e.target.files;
    if (!files) return;
    setAttachments((prev: File[]) => [...prev, ...Array.from(files)]);
    e.currentTarget.value = "";
  };

  const handleRemoveAttachment = (index: number) => {
    setAttachments((prev: File[]) => prev.filter((_, i: number) => i !== index));
  };

  const canSend = (messageInput.trim().length > 0 || attachments.length > 0) && !disabled;

  return (
    <>
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
          disabled={disabled}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (canSend) {
                onSend();
              }
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
            "&.Mui-disabled": {
               opacity: 0.6
            }
          }}
          InputProps={{
            style: { color: '#fff' },
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  onClick={onAttachClick}
                  disabled={disabled}
                  edge="end"
                  aria-label="attach"
                  sx={{
                    color: "#ff4fff",
                    "&.Mui-disabled": { color: "rgba(255,255,255,0.3)" }
                  }}
                >
                  <AttachFileIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />

        <IconButton
          color="primary"
          onClick={onSend}
          disabled={!canSend}
          aria-label="send"
          sx={{
            bgcolor: canSend ? "#a020f0" : "rgba(160, 32, 240, 0.3)",
            color: "#fff",
            "&:hover": { bgcolor: canSend ? "#ff4fff" : "rgba(160, 32, 240, 0.3)" },
            "&.Mui-disabled": {
                color: "rgba(255,255,255,0.3)",
                bgcolor: "rgba(160, 32, 240, 0.1)"
            }
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
                disabled={disabled}
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
    </>
  );
};

export default MessageInput;
