import React from "react";
import { GP } from "../../styles/theme";

export default function IconBtn({ children, onClick, title, danger }) {
  return (
    <button
      className="icon-btn"
      title={title}
      onClick={onClick}
      style={{
        width: 36,
        height: 36,
        borderRadius: "50%",
        border: "none",
        background: "transparent",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "all 0.15s",
        color: danger ? GP.coral : GP.textSecondary,
        fontSize: 16,
      }}
    >
      {children}
    </button>
  );
}
