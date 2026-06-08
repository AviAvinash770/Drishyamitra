import React, { useState, useEffect, useCallback } from "react";
import { api } from "../../api";
import { GP } from "../../styles/theme";
import Avatar from "../common/Avatar";
import PersonPhotosModal from "../gallery/PersonPhotosModal";

export default function PeoplePage({ showNotif, setPage, setShareParams }) {
  const [persons, setPersons] = useState([]);
  const [unrecognized, setUnrecognized] = useState([]);
  const [labeling, setLabeling] = useState(null);
  const [labelName, setLabelName] = useState("");
  const [viewingPerson, setViewingPerson] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const pList = await api.faces.persons();
      setPersons(pList);
      
      const unrecognisedList = await api.faces.unrecognized();
      setUnrecognized(unrecognisedList);
    } catch (err) {
      showNotif("Failed to load people and face data.", "error");
    }
  }, [showNotif]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function saveLabel(faceId, name) {
    if (!name.trim()) return;
    try {
      const res = await api.faces.label(faceId, name);
      showNotif(`Face labeled as "${name}"! Auto-linked ${res.auto_linked} other faces.`, "success");
      setLabeling(null);
      setLabelName("");
      loadData();
    } catch (err) {
      showNotif("Failed to save face label.", "error");
    }
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, flex: 1, color: GP.textPrimary }}>People & Faces</h2>
      </div>

      {/* Unrecognized */}
      <div style={{ background: GP.white, borderRadius: 16, padding: "20px 24px", boxShadow: GP.shadow1, marginBottom: 24 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: GP.textPrimary, marginBottom: 4 }}>Unrecognized Faces</div>
        <div style={{ fontSize: 12, color: GP.textSecondary, marginBottom: 16 }}>Label these to improve face recognition accuracy</div>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {unrecognized.map((face) => (
            <div key={face.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <div style={{
                width: 64,
                height: 64,
                borderRadius: "50%",
                background: GP.surface,
                border: `2px dashed ${GP.border}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 26,
                cursor: "pointer",
              }}>❓</div>
              <button
                onClick={() => { setLabeling(face.id); setLabelName(""); }}
                style={{
                  padding: "4px 14px",
                  borderRadius: 20,
                  border: "none",
                  background: GP.blueLight,
                  color: GP.blue,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >Label</button>
            </div>
          ))}
          {unrecognized.length === 0 && (
            <div style={{ fontSize: 13, color: GP.textSecondary, padding: "10px 0" }}>
              🎉 All detected faces have been successfully recognized!
            </div>
          )}
        </div>
        {labeling !== null && (
          <div style={{ marginTop: 16, padding: "16px", background: GP.surface, borderRadius: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <input
              style={{
                flex: 1,
                padding: "9px 14px",
                border: `1px solid ${GP.blue}`,
                borderRadius: 24,
                fontSize: 13,
                background: GP.white,
              }}
              placeholder="Enter person's name…"
              value={labelName}
              onChange={e => setLabelName(e.target.value)}
              autoFocus
              onKeyDown={e => {
                if (e.key === "Enter" && labelName.trim()) {
                  saveLabel(labeling, labelName);
                }
              }}
            />
            <button
              onClick={() => saveLabel(labeling, labelName)}
              style={{ padding: "9px 18px", background: GP.blue, color: "#fff", border: "none", borderRadius: 24, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >Save</button>
            <button onClick={() => setLabeling(null)} style={{ padding: "9px 14px", background: "none", border: `1px solid ${GP.border}`, borderRadius: 24, fontSize: 13, cursor: "pointer", color: GP.textSecondary }}>Skip</button>
          </div>
        )}
      </div>

      {/* Person grid */}
      <h3 style={{ fontSize: 15, fontWeight: 600, color: GP.textPrimary, marginBottom: 16 }}>Recognized People</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
        {persons.map((p, i) => (
          <div key={p.id} className="person-card" onClick={() => setViewingPerson(p)} style={{
            background: GP.white,
            borderRadius: 16,
            padding: "20px 16px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12,
            cursor: "pointer",
            boxShadow: GP.shadow1,
            transition: "all 0.25s",
            opacity: p.name === "Unknown" ? 0.6 : 1,
            animation: `fadeUp ${0.3 + i * 0.06}s ease both`,
          }}>
            <Avatar person={p} size={64} />
            <div style={{ textAlign: "center" }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: GP.textPrimary }}>{p.name}</div>
              <div style={{ color: GP.textTertiary, fontSize: 12, marginTop: 3 }}>{p.photoCount || p.photo_count || 0} photos</div>
            </div>
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "center" }}>
              {(p.tags || []).map(t => (
                <span key={t} style={{ padding: "3px 10px", background: p.bg, color: p.color, borderRadius: 20, fontSize: 11, fontWeight: 500 }}>{t}</span>
              ))}
            </div>
            <div style={{ display: "flex", gap: 8, width: "100%" }}>
              <button
                onClick={(e) => { e.stopPropagation(); setViewingPerson(p); }}
                style={{ flex: 1, padding: "7px", background: GP.surface, border: `1px solid ${GP.border}`, borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: "pointer", color: GP.textPrimary }}
              >View</button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShareParams({ targetType: "person", selectedPerson: p.name });
                  setPage("delivery");
                }}
                style={{ flex: 1, padding: "7px", background: GP.blueLight, border: "none", borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: "pointer", color: GP.blue }}
              >Share</button>
            </div>
          </div>
        ))}
      </div>
      {viewingPerson && (
        <PersonPhotosModal person={viewingPerson} onClose={() => setViewingPerson(null)} />
      )}
    </div>
  );
}
