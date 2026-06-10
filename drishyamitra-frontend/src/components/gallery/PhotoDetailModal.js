import React, { useState, useEffect, useCallback } from "react";
import { GP } from "../../styles/theme";
import IconBtn from "../common/IconBtn";
import { api } from "../../api";

export default function PhotoDetailModal({ photo, onClose, onDelete, onShare, photos, currentIndex, onIndexChange, onReLabel }) {
  const [assignLabelStr, setAssignLabelStr] = useState("");
  const [persons, setPersons] = useState([]);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isMovingAlbum, setIsMovingAlbum] = useState(false);

  useEffect(() => {
    api.faces.persons().then(p => setPersons(p)).catch(console.error);
  }, []);

  const activePhoto = photos && currentIndex !== undefined 
    ? (photos[currentIndex] || photos[photos.length - 1] || photo) 
    : photo;

  const activePhotoEventAlbum = activePhoto?.album_names?.find(name => ["Birthdays", "Weddings", "Anniversaries"].includes(name)) || "";

  const handleMoveAlbum = async (e) => {
    const targetAlbum = e.target.value;
    if (!activePhoto) return;
    setIsMovingAlbum(true);
    try {
      await api.photos.moveAlbum(activePhoto.id, targetAlbum);
      if (onReLabel) {
        await onReLabel(activePhoto.id, assignLabelStr);
      }
    } catch (err) {
      alert("Failed to move photo to event folder.");
    } finally {
      setIsMovingAlbum(false);
    }
  };

  const handleAssignLabel = async () => {
    if (!assignLabelStr.trim() || !activePhoto) return;
    setIsAssigning(true);
    try {
      const res = await api.photos.assignLabel(activePhoto.id, assignLabelStr);
      setAssignLabelStr("");
      if (onReLabel) {
        await onReLabel(activePhoto.id, assignLabelStr);
      } else {
        alert(res.message);
        if (onClose) onClose();
      }
    } catch (err) {
      alert("Failed to assign label");
    } finally {
      setIsAssigning(false);
    }
  };

  const handlePrev = useCallback(() => {
    if (photos && onIndexChange && currentIndex !== undefined) {
      const prevIdx = (currentIndex - 1 + photos.length) % photos.length;
      onIndexChange(prevIdx);
      setAssignLabelStr("");
    }
  }, [photos, currentIndex, onIndexChange]);

  const handleNext = useCallback(() => {
    if (photos && onIndexChange && currentIndex !== undefined) {
      const nextIdx = (currentIndex + 1) % photos.length;
      onIndexChange(nextIdx);
      setAssignLabelStr("");
    }
  }, [photos, currentIndex, onIndexChange]);

  useEffect(() => {
    const handler = e => { 
      // Don't intercept arrows when user is typing in an input/select/textarea
      const tag = (e.target.tagName || "").toLowerCase();
      const isEditable = tag === "input" || tag === "select" || tag === "textarea" || e.target.isContentEditable;
      if (e.key === "Escape") onClose(); 
      if (isEditable) return;
      if (e.key === "ArrowLeft") handlePrev();
      if (e.key === "ArrowRight") handleNext();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose, handlePrev, handleNext]);

  if (!activePhoto) return null;

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()} style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.85)",
      backdropFilter: "blur(10px)",
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
        width: "90%",
        maxWidth: 850,
        maxHeight: "90vh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        animation: "scaleIn 0.25s cubic-bezier(0.34,1.56,0.64,1)",
      }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", padding: "16px 20px", borderBottom: `1px solid ${GP.border}`, gap: 12 }}>
          <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: GP.textPrimary }}>
            {activePhoto.name} {photos && currentIndex !== undefined ? `(${currentIndex + 1} of ${photos.length})` : ""}
          </span>
          {onShare && (
            <button
              onClick={() => onShare(activePhoto)}
              style={{
                background: GP.blueLight, color: GP.blue, border: "none", borderRadius: 20,
                padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer"
              }}
            >
              Share
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(activePhoto.id)}
              style={{
                background: "#fce8e6", color: GP.coral, border: "none", borderRadius: 20,
                padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer"
              }}
            >
              Delete
            </button>
          )}
          <IconBtn onClick={onClose}>✕</IconBtn>
        </div>
        
        {/* Assign Label Bar */}
        <div style={{ padding: "12px 20px", background: GP.blueLight, borderBottom: `1px solid ${GP.border}`, display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, color: GP.blue, fontWeight: 600 }}>Assign / Change Person:</span>
          <input 
            list="person-list"
            value={assignLabelStr}
            onChange={e => setAssignLabelStr(e.target.value)}
            placeholder="Type a name or choose existing..."
            style={{ flex: 1, padding: "8px 12px", border: `1px solid ${GP.border}`, borderRadius: 20, fontSize: 13, outline: "none" }}
            disabled={isAssigning}
          />
          <datalist id="person-list">
            {persons.map(p => <option key={p.id} value={p.name} />)}
          </datalist>
          <button 
            onClick={handleAssignLabel}
            disabled={!assignLabelStr.trim() || isAssigning}
            style={{
              background: GP.blue, color: "#fff", border: "none", padding: "8px 16px",
              borderRadius: 20, fontSize: 13, fontWeight: 600,
              cursor: (!assignLabelStr.trim() || isAssigning) ? "not-allowed" : "pointer",
              opacity: (!assignLabelStr.trim() || isAssigning) ? 0.6 : 1, boxShadow: GP.shadow1
            }}
          >
            {isAssigning ? "Assigning..." : "Assign to Person"}
          </button>
        </div>

        {/* Move to Event Folder Bar */}
        <div style={{ padding: "12px 20px", background: "#fcf8e3", borderBottom: `1px solid ${GP.border}`, display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, color: "#8a6d3b", fontWeight: 600 }}>Move to Event Folder:</span>
          <select
            value={activePhotoEventAlbum}
            onChange={handleMoveAlbum}
            style={{ padding: "8px 12px", border: `1px solid ${GP.border}`, borderRadius: 20, fontSize: 13, outline: "none", background: "#fff", cursor: "pointer", flex: 1 }}
            disabled={isMovingAlbum}
          >
            <option value="">None / Remove from events</option>
            <option value="Birthdays">🎂 Birthdays</option>
            <option value="Weddings">💍 Weddings</option>
            <option value="Anniversaries">❤️ Anniversaries</option>
          </select>
        </div>

        {/* Photo Viewport with Navigation overlays */}
        <div style={{
          height: "72vh",
          background: activePhoto.url ? "#1a1a1a" : `linear-gradient(135deg, ${activePhoto.palette?.[0] || "#e8d5b7"}, ${activePhoto.palette?.[1] || "#d4a574"})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 80,
          overflow: "hidden",
          position: "relative"
        }}>
          <style>{`
            @keyframes fadePhotoDetail {
              from { opacity: 0; transform: scale(0.97); }
              to { opacity: 1; transform: scale(1); }
            }
            .photo-fade-detail {
              animation: fadePhotoDetail 0.25s ease-out forwards;
            }
          `}</style>
          
          {/* Left Arrow Overlay */}
          {photos && photos.length > 1 && (
            <button
              onClick={handlePrev}
              style={{
                position: "absolute", left: 16, top: "50%", transform: "translateY(-50%)",
                background: "rgba(255,255,255,0.15)", color: "#fff",
                borderRadius: "50%", width: 48, height: 48, fontSize: 20, cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", zIndex: 10,
                backdropFilter: "blur(8px)",
                border: "1px solid rgba(255,255,255,0.2)",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                transition: "all 0.2s"
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = "rgba(255,255,255,0.3)";
                e.currentTarget.style.transform = "translateY(-50%) scale(1.1)";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = "rgba(255,255,255,0.15)";
                e.currentTarget.style.transform = "translateY(-50%) scale(1)";
              }}
            >
              ◀
            </button>
          )}

          {activePhoto.url ? (
            <img 
              key={activePhoto.id}
              className="photo-fade-detail"
              src={activePhoto.url} 
              alt={activePhoto.name} 
              style={{ width: "100%", height: "100%", objectFit: "contain" }} 
            />
          ) : (
            <div key={activePhoto.id} className="photo-fade-detail" style={{ fontSize: 80 }}>
              {activePhoto.emoji || "📸"}
            </div>
          )}

          {/* Right Arrow Overlay */}
          {photos && photos.length > 1 && (
            <button
              onClick={handleNext}
              style={{
                position: "absolute", right: 16, top: "50%", transform: "translateY(-50%)",
                background: "rgba(255,255,255,0.15)", color: "#fff",
                borderRadius: "50%", width: 48, height: 48, fontSize: 20, cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", zIndex: 10,
                backdropFilter: "blur(8px)",
                border: "1px solid rgba(255,255,255,0.2)",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                transition: "all 0.2s"
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = "rgba(255,255,255,0.3)";
                e.currentTarget.style.transform = "translateY(-50%) scale(1.1)";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = "rgba(255,255,255,0.15)";
                e.currentTarget.style.transform = "translateY(-50%) scale(1)";
              }}
            >
              ▶
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
