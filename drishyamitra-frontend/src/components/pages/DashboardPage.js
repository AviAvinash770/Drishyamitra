import React, { useState, useEffect } from "react";
import { api } from "../../api";
import { GP } from "../../styles/theme";
import StatCard from "../common/StatCard";
import ProgressBar from "../common/ProgressBar";
import { FOLDERS, MEMORIES } from "../../constants/mockData";

export default function DashboardPage({ setPage, showNotif, onOpenAnalytics }) {
  const [stats, setStats] = useState(null);
  const [albums, setAlbums] = useState([]);

  useEffect(() => {
    async function loadData() {
      try {
        const dashboardStats = await api.analytics.dashboard();
        setStats(dashboardStats);
        
        const albumList = await api.albums.list();
        setAlbums(albumList);
      } catch (err) {
        showNotif("Failed to load dashboard data.", "error");
      }
    }
    loadData();
  }, [showNotif]);

  const totalPhotos = stats?.total_photos ?? 312;
  const peopleTagged = stats?.total_people ?? 5;
  const sharedCount = stats?.total_deliveries ?? 24;
  const untaggedFaces = stats?.unrecognised_faces ?? 18;

  const displayAlbums = albums.length > 0 ? albums : FOLDERS;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      {/* Memories section */}
      <section>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: GP.textPrimary }}>Memories</h2>
          <button style={{ background: "none", border: "none", color: GP.blue, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>See all</button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
          {MEMORIES.map((m, i) => (
            <div key={m.title} className="memory-card" style={{
              borderRadius: 16,
              overflow: "hidden",
              cursor: "pointer",
              background: `linear-gradient(135deg, ${m.palette[0]}, ${m.palette[1]})`,
              boxShadow: GP.shadow1,
              transition: "all 0.25s",
              animation: `fadeUp ${0.3 + i * 0.08}s ease both`,
              position: "relative",
            }}>
              <div style={{ height: 120, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 48 }}>{m.emoji}</div>
              <div style={{ padding: "12px 14px 14px", background: "rgba(0,0,0,0.18)", backdropFilter: "blur(2px)" }}>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.8)", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.5px" }}>{m.label}</div>
                <div style={{ fontSize: 14, color: "#fff", fontWeight: 700, marginTop: 2 }}>{m.title}</div>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.7)", marginTop: 2 }}>{m.count} photos</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <StatCard label="Total Photos" value={totalPhotos} icon="📸" color={GP.blue} bg={GP.blueLight} />
        <StatCard label="People Tagged" value={peopleTagged} icon="👤" color={GP.teal} bg={GP.tealLight} />
        <StatCard label="Shared Deliveries" value={sharedCount} icon="↗" color={GP.amber} bg={GP.amberLight} />
        <StatCard label="Untagged Faces" value={untaggedFaces} icon="❓" color={GP.coral} bg={GP.coralLight} />
      </div>

      {/* Smart Albums */}
      <div style={{ background: GP.white, borderRadius: 16, padding: "20px 24px", boxShadow: GP.shadow1 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: GP.textPrimary }}>📁 Smart Albums</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
          {displayAlbums.map(f => (
            <div key={f.name} className="folder-row" style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 8px",
              cursor: "pointer",
              transition: "all 0.15s",
            }}>
              <div style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: f.bg,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
                flexShrink: 0
              }}>{f.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 13, fontWeight: 500, color: GP.textPrimary }}>{f.name}</span>
                  <span style={{ fontSize: 12, color: GP.textTertiary }}>{f.count || f.photo_count || 0}</span>
                </div>
                <ProgressBar value={Math.min((f.count || f.photo_count || 0) / 1.3, 100)} color={f.color} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ background: GP.white, borderRadius: 16, padding: "20px 24px", boxShadow: GP.shadow1 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: GP.textPrimary }}>⚡ Quick Actions</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {[
            { icon: "📤", label: "Upload Photos", color: GP.blue, bg: GP.blueLight, action: () => setPage("gallery") },
            { icon: "🔍", label: "Search by Face", color: GP.teal, bg: GP.tealLight, action: () => setPage("people") },
            { icon: "💬", label: "Ask AI", color: GP.purple, bg: GP.purpleLight, action: () => setPage("chat") },
            { icon: "📊", label: "Analytics", color: GP.coral, bg: GP.coralLight, action: onOpenAnalytics },
          ].map(a => (
            <button key={a.label} className="quick-action" onClick={a.action} style={{
              background: a.bg,
              border: "none",
              borderRadius: 16,
              padding: "18px 12px",
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              boxShadow: GP.shadow1,
              transition: "all 0.2s",
            }}>
              <span style={{ fontSize: 28 }}>{a.icon}</span>
              <span style={{ fontSize: 12, color: a.color, fontWeight: 600 }}>{a.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
