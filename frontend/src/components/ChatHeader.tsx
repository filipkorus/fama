import React from "react";

interface ChatHeaderProps {
  username: string | null;
  isConnected: boolean;
  onLogout: () => void;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({ username, isConnected, onLogout }) => {
  return (
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
        <span style={{ color: "#999", fontSize: "12px" }}>– secure chat</span>
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
          onClick={onLogout}
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
  );
};

export default ChatHeader;
