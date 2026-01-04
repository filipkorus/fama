import React from "react";
import { Box, TextField, IconButton, InputAdornment, Stack, Chip } from "@mui/material";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import SendIcon from "@mui/icons-material/Send";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import { MAX_FILE_SIZE } from '../config';

interface MessageInputProps {
  messageInput: string;
  setMessageInput: (value: string) => void;
  attachments: File[];
  setAttachments: (files: File[] | ((prev: File[]) => File[])) => void;
  onSend: () => void;
  onSendAttachment?: (file: File) => void;
  disabled?: boolean;
  fileInputRef: React.RefObject<HTMLInputElement>;
}

const MessageInput: React.FC<MessageInputProps> = ({
  messageInput,
  setMessageInput,
  attachments,
  setAttachments,
  onSend,
  onSendAttachment,
  fileInputRef,
  disabled = false,
}) => {
  const [isDragging, setIsDragging] = React.useState(false);
  
  const onAttachClick = () => fileInputRef.current?.click();

  const validateAndAddFiles = (files: FileList | File[]) => {
    const validFiles: File[] = [];
    const invalidFiles: string[] = [];
    const maxSizeMB = (MAX_FILE_SIZE / (1024 * 1024)).toFixed(0);
    
    Array.from(files).forEach(file => {
      if (file.size > MAX_FILE_SIZE) {
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        invalidFiles.push(`${file.name} (${sizeMB} MB)`);
      } else {
        validFiles.push(file);
      }
    });

    if (invalidFiles.length > 0) {
      alert(`Następujące pliki są zbyt duże (maksymalny rozmiar: ${maxSizeMB} MB):\n${invalidFiles.join('\n')}`);
    }

    if (validFiles.length > 0) {
      setAttachments((prev: File[]) => [...prev, ...validFiles]);
    }
  };

  const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    const files = e.target.files;
    if (!files) return;
    validateAndAddFiles(files);
    e.currentTarget.value = "";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      validateAndAddFiles(files);
    }
  };

  const handleRemoveAttachment = (index: number) => {
    setAttachments((prev: File[]) => prev.filter((_, i: number) => i !== index));
  };

  const handleSendClick = () => {
    if (!canSend) return;

    if (attachments.length > 0 && onSendAttachment) {
      attachments.forEach(file => onSendAttachment(file));
    } else {
      onSend();
    }
  };

  const canSend = (messageInput.trim().length > 0 || attachments.length > 0) && !disabled;

  return (
    <>
      <Box
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        sx={{
          display: "flex",
          gap: 1,
          alignItems: "flex-end",
          px: 3,
          pb: 3,
          position: "relative",
          "&::before": isDragging ? {
            content: '"Upuść pliki tutaj"',
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            bgcolor: "rgba(160, 32, 240, 0.2)",
            border: "2px dashed #ff4fff",
            borderRadius: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#ff4fff",
            fontSize: "1.2rem",
            fontWeight: "bold",
            pointerEvents: "none",
            zIndex: 10,
          } : {}
        }}
      >
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder="Napisz wiadomość..."
          value={messageInput}
          onChange={(e) => setMessageInput(e.target.value)}
          disabled={disabled}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (canSend) {
                if (attachments.length > 0 && onSendAttachment) {
                  // Send each attachment as a separate message
                  attachments.forEach(file => {
                    onSendAttachment(file);
                  });
                } else {
                  onSend();
                }
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
                  aria-label="attach file"
                  title="Przeciągnij pliki tutaj"
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
          onClick={handleSendClick}
          disabled={!canSend}
          aria-label="send message"
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
        id="file-input"
        aria-label="Upload file attachment"
        title="Upload file attachment"
        style={{ display: "none" }}
        multiple
        onChange={handleFileChange}
      />
    </>
  );
};

export default MessageInput;
