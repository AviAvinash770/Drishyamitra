import React, { useState } from "react";
import { GP } from "../../styles/theme";
import { api } from "../../api";

export default function PhotoCard({ photo, onClick, style, selected, selectMode, onSelect, onShareClick }) {
  const [fav, setFav] = useState(photo.favorite);

  const handleFavClick = async (e) => {
    e.stopPropagation();
    const newFav = !fav;
    setFav(newFav);
    try {
      await api.photos.toggleFavorite(photo.id);
    } catch (err) {
      console.error("Failed to toggle favorite on backend:", err);
      setFav(fav); // Revert state
    }
  };

  const handleCardClick = (e) => {
    if (selectMode) {
      if (onSelect) onSelect(photo.id);
    } else {
      if (onClick) onClick();
    }
  };

  return (
    <div
      className="photo-card"
      onClick={handleCardClick}
      style={{
        borderRadius: 12,
        overflow: "hidden",
        cursor: "pointer",
        position: "relative",
        transition: "transform 0.2s, box-shadow 0.2s, border-color 0.2s",
        border: selected ? `3px solid ${GP.blue}` : `3px solid transparent`,
        boxShadow: selected ? GP.shadow3 : GP.shadow1,
        transform: selected ? "scale(0.98)" : "none",
        background: GP.white,
        ...style,
      }}
    >
      {/* Checkbox overlay for select mode */}
      {selectMode && (
        <div style={{
          position: "absolute",
          top: 10,
          right: 10,
          width: 24,
          height: 24,
          borderRadius: "50%",
          background: selected ? GP.blue : "rgba(255, 255, 255, 0.8)",
          border: `2px solid ${selected ? GP.blue : "rgba(0, 0, 0, 0.2)"}`,
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#fff",
          fontSize: 12,
          fontWeight: "bold",
          boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
          transition: "all 0.15s",
        }}>
          {selected && "✓"}
        </div>
      )}

      {/* Photo placeholder */}
      <div style={{
        height: photo.height || 180,
        background: photo.url ? "none" : `linear-gradient(135deg, ${photo.palette?.[0] || "#e8d5b7"}, ${photo.palette?.[1] || "#d4a574"})`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 48,
        position: "relative",
        overflow: "hidden",
      }}>
        {photo.url ? (
          <img src={photo.url} alt={photo.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : (
          photo.emoji
        )}
        {/* Hover overlay */}
        <div className="photo-overlay" style={{
          position: "absolute",
          inset: 0,
          background: "rgba(0,0,0,0.25)",
          opacity: 0,
          transition: "opacity 0.2s",
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "flex-end",
          padding: 10,
          gap: 6,
        }}>
          <button onClick={handleFavClick} style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "rgba(255,255,255,0.9)",
            border: "none",
            cursor: "pointer",
            fontSize: 15,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>{fav ? "❤️" : "🤍"}</button>
          <button onClick={e => { e.stopPropagation(); if (onShareClick) onShareClick(); }} style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "rgba(255,255,255,0.9)",
            border: "none",
            cursor: "pointer",
            fontSize: 15,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>↗</button>
        </div>
        {/* Badges */}
        {photo.recognized && (
          <div style={{
            position: "absolute",
            top: 8,
            left: 8,
            background: "rgba(26,115,232,0.9)",
            color: "#fff",
            fontSize: 10,
            fontWeight: 600,
            padding: "3px 8px",
            borderRadius: 20,
            backdropFilter: "blur(4px)",
          }}>✓ Tagged</div>
        )}
      </div>
      <div style={{ padding: "8px 12px 10px" }}>
        <div style={{
          fontSize: 12,
          color: GP.textPrimary,
          fontWeight: 500,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap"
        }}>{photo.name}</div>
        <div style={{ fontSize: 11, color: GP.textTertiary, marginTop: 2 }}>{photo.persons?.slice(0, 2).join(", ")}</div>
      </div>
    </div>
  );
}
