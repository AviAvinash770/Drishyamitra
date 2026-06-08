import React from "react";
import { GP } from "../../styles/theme";

export default function StatCard({ label, value, icon, color, bg }) {
  return (
    <div className="stat-chip" style={{
      background: GP.white,
      borderRadius: 16,
      padding: "20px 24px",
      boxShadow: GP.shadow1,
      display: "flex",
      flexDirection: "column",
      gap: 8,
      transition: "box-shadow 0.2s",
      animation: "fadeUp 0.4s ease both",
    }}>
      <div style={{
        width: 40,
        height: 40,
        borderRadius: 12,
        background: bg || GP.blueLight,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 20
      }}>{icon}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || GP.textPrimary, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 13, color: GP.textSecondary, fontWeight: 500 }}>{label}</div>
    </div>
  );
}
