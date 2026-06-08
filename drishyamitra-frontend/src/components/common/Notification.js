import React, { useEffect } from "react";
import { GP } from "../../styles/theme";

export default function Notification({ message, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  const cfg = {
    success: { icon: "✓", color: GP.green, bg: GP.greenLight },
    error: { icon: "✗", color: GP.coral, bg: GP.coralLight },
    info: { icon: "ℹ", color: GP.blue, bg: GP.blueLight },
  }[type] || { icon: "ℹ", color: GP.blue, bg: GP.blueLight };

  return (
    <div style={{
      position: "fixed",
      bottom: 24,
      right: 24,
      zIndex: 400,
      background: GP.white,
      borderRadius: 12,
      padding: "14px 20px",
      boxShadow: GP.shadow3,
      display: "flex",
      alignItems: "center",
      gap: 12,
      animation: "notifSlide 0.3s cubic-bezier(0.34,1.56,0.64,1) both",
      maxWidth: 340,
      minWidth: 240,
    }}>
      <div style={{
        width: 32,
        height: 32,
        borderRadius: 8,
        background: cfg.bg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: cfg.color,
        fontSize: 15,
        fontWeight: 700,
        flexShrink: 0
      }}>{cfg.icon}</div>
      <span style={{ fontSize: 13, color: GP.textPrimary, flex: 1, lineHeight: 1.4 }}>{message}</span>
      <button onClick={onClose} style={{ background: "none", border: "none", color: GP.textTertiary, cursor: "pointer", fontSize: 18, lineHeight: 1, padding: 2 }}>×</button>
    </div>
  );
}
