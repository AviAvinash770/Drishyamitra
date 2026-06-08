import React from "react";
import { GP } from "../../styles/theme";

export default function Chip({ label, active, onClick, color }) {
  return (
    <button
      className={`chip ${active ? "chip-active" : ""}`}
      onClick={onClick}
      style={{
        padding: "6px 16px",
        borderRadius: 20,
        border: `1px solid ${active ? (color || GP.blue) : GP.border}`,
        background: active ? GP.blueLight : GP.white,
        color: active ? (color || GP.blue) : GP.textSecondary,
        fontSize: 13,
        fontWeight: 500,
        cursor: "pointer",
        transition: "all 0.15s",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
}
