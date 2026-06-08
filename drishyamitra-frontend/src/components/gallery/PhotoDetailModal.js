import React, { useEffect } from "react";
import { GP } from "../../styles/theme";
import IconBtn from "../common/IconBtn";
import { MOCK_PERSONS } from "../../constants/mockData";

export default function PhotoDetailModal({ photo, onClose, onDelete, onShare }) {
  useEffect(() => {
    const handler = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()} style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.7)",
      backdropFilter: "blur(8px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 200,
      padding: 20,
      animation: "fadeIn 0.2s",
    }}>
      <div style={{
        background: GP.white,
        borderRadius: 20,
        width: "100%",
        maxWidth: 560,
        maxHeight: "90vh",
        overflowY: "auto",
        animation: "scaleIn 0.25s cubic-bezier(0.34,1.56,0.64,1)",
      }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", padding: "16px 20px", borderBottom: `1px solid ${GP.border}` }}>
          <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: GP.textPrimary }}>{photo.name}</span>
          <IconBtn onClick={onClose}>✕</IconBtn>
        </div>
        {/* Photo */}
        <div style={{
          height: 280,
          background: photo.url ? "none" : `linear-gradient(135deg, ${photo.palette?.[0] || "#e8d5b7"}, ${photo.palette?.[1] || "#d4a574"})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 80,
          overflow: "hidden",
        }}>
          {photo.url ? (
            <img src={photo.url} alt={photo.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            photo.emoji
          )}
        </div>
        {/* Actions */}
        <div style={{ display: "flex", gap: 0, padding: "8px 12px", borderBottom: `1px solid ${GP.border}`, justifyContent: "center" }}>
          {[["❤️", "Favorite"], ["↗", "Share"], ["⬇", "Download"], ["🗑", "Delete"]].map(([icon, label]) => (
            <button key={label} style={{
              flex: 1,
              background: "none",
              border: "none",
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 4,
              padding: "12px 8px",
              color: GP.textSecondary,
              fontSize: 12,
              borderRadius: 8,
              transition: "background 0.15s",
            }}
              onMouseEnter={e => e.currentTarget.style.background = GP.surface}
              onMouseLeave={e => e.currentTarget.style.background = "none"}
              onClick={async () => {
                if (label === "Delete" && onDelete) {
                  if (window.confirm("Are you sure you want to delete this photo?")) {
                    onDelete(photo.id);
                  }
                } else if (label === "Share" && onShare) {
                  onShare();
                }
              }}
            >
              <span style={{ fontSize: 20 }}>{icon}</span>
              {label}
            </button>
          ))}
        </div>
        {/* Info */}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {[
              ["📅 Date", photo.date],
              ["💾 Size", photo.size],
              ["📁 Album", photo.folder],
              ["🤖 Status", photo.recognized ? "Faces tagged" : "Untagged"],
            ].map(([k, v]) => (
              <div key={k}>
                <div style={{ fontSize: 11, color: GP.textTertiary, fontWeight: 500, marginBottom: 4 }}>{k}</div>
                <div style={{ fontSize: 13, color: GP.textPrimary, fontWeight: 500 }}>{v}</div>
              </div>
            ))}
          </div>
          {photo.persons && photo.persons.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: GP.textTertiary, fontWeight: 500, marginBottom: 8 }}>👤 People</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {photo.persons.map(p => {
                  const person = MOCK_PERSONS.find(m => m.name === p) || { emoji: "👤", bg: GP.blueLight, color: GP.blue, initials: p[0] };
                  return (
                    <div key={p} style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "4px 12px 4px 6px",
                      background: person.bg,
                      borderRadius: 20,
                      color: person.color,
                      fontSize: 12,
                      fontWeight: 500,
                    }}>
                      <span>{person.emoji}</span>{p}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
