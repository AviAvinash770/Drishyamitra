import React, { useState, useEffect } from "react";
import { api } from "../../api";
import { GP } from "../../styles/theme";
import IconBtn from "../common/IconBtn";
import ProgressBar from "../common/ProgressBar";
import StatCard from "../common/StatCard";
import { MOCK_PERSONS } from "../../constants/mockData";

export default function AnalyticsModal({ onClose }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.analytics.dashboard().then(res => setStats(res)).catch(err => console.error(err));
  }, []);

  const bars = stats?.photos_per_month && stats.photos_per_month.length > 0
    ? stats.photos_per_month.map(item => ({ month: item.month, count: item.count }))
    : [
        { month: "Jan", count: 45 }, { month: "Feb", count: 32 }, { month: "Mar", count: 67 },
        { month: "Apr", count: 89 }, { month: "May", count: 54 }, { month: "Jun", count: 76 },
      ];
  const maxCount = Math.max(...bars.map(b => b.count || 1), 1);

  const displayPeople = stats?.people_stats && stats.people_stats.length > 0
    ? stats.people_stats
    : MOCK_PERSONS.slice(0, 5);

  const storageUsed = stats?.storage?.used_gb ?? 4.2;
  const storageLimit = stats?.storage?.limit_gb ?? 10.0;
  const storagePct = stats?.storage?.used_pct ?? 42.0;
  const storageRem = stats?.storage?.remaining_gb ?? 5.8;

  useEffect(() => {
    const handler = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()} style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.55)",
      backdropFilter: "blur(6px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 200,
      padding: 24,
      animation: "fadeIn 0.2s",
    }}>
      <div style={{
        background: GP.surface,
        borderRadius: 20,
        width: "100%",
        maxWidth: 720,
        maxHeight: "90vh",
        overflowY: "auto",
        animation: "scaleIn 0.25s cubic-bezier(0.34,1.56,0.64,1)",
        boxShadow: GP.shadow3,
      }}>
        {/* Header */}
        <div style={{
          display: "flex",
          alignItems: "center",
          padding: "18px 24px",
          background: GP.white,
          borderRadius: "20px 20px 0 0",
          borderBottom: `1px solid ${GP.border}`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: GP.blueLight, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>📊</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: GP.textPrimary }}>Storage & Analytics</div>
              <div style={{ fontSize: 12, color: GP.textTertiary, marginTop: 1 }}>Insights about your photo library</div>
            </div>
          </div>
          <IconBtn onClick={onClose}>✕</IconBtn>
        </div>

        <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Storage breakdown */}
          <div style={{ background: GP.white, borderRadius: 16, padding: "20px 24px", boxShadow: GP.shadow1 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: GP.textPrimary, marginBottom: 16 }}>💾 Storage Breakdown</h3>
            <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 16 }}>
              {/* Donut visual */}
              <div style={{ position: "relative", width: 80, height: 80, flexShrink: 0 }}>
                <svg width="80" height="80" viewBox="0 0 80 80">
                  <circle cx="40" cy="40" r="30" fill="none" stroke={GP.borderLight} strokeWidth="12" />
                  <circle cx="40" cy="40" r="30" fill="none" stroke={GP.blue} strokeWidth="12"
                    strokeDasharray={`${(storagePct / 100) * 188.5} 188.5`} strokeLinecap="round"
                    transform="rotate(-90 40 40)" style={{ transition: "stroke-dasharray 1s ease" }} />
                </svg>
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, color: GP.textPrimary }}>{Math.round(storagePct)}%</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: GP.textPrimary }}>{storageUsed} <span style={{ fontSize: 14, fontWeight: 500, color: GP.textSecondary }}>of {storageLimit} GB</span></div>
                <div style={{ fontSize: 12, color: GP.textTertiary, marginTop: 4 }}>{storageRem} GB remaining</div>
                <div style={{ marginTop: 10 }}><ProgressBar value={storagePct} /></div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
              {[
                { label: "Photos", size: `${Math.round(storageUsed * 0.74 * 10) / 10} GB`, color: GP.blue, pct: 74 },
                { label: "AI Cache", size: `${Math.round(storageUsed * 0.17 * 10) / 10} GB`, color: GP.purple, pct: 17 },
                { label: "Thumbnails", size: `${Math.round(storageUsed * 0.09 * 10) / 10} GB`, color: GP.teal, pct: 9 },
              ].map(s => (
                <div key={s.label} style={{ background: GP.surface, borderRadius: 10, padding: "12px 14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: s.color }} />
                    <span style={{ fontSize: 11, color: GP.textSecondary, fontWeight: 500 }}>{s.label}</span>
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: GP.textPrimary }}>{s.size}</div>
                  <div style={{ fontSize: 10, color: GP.textTertiary, marginTop: 2 }}>{s.pct}% of used</div>
                </div>
              ))}
            </div>
          </div>

          {/* Stats row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
            <StatCard label="Faces Detected" value={stats?.total_faces_detected ?? 847} icon="🔍" color={GP.blue} bg={GP.blueLight} />
            <StatCard label="Auto-sorted" value={stats?.recognised_faces ?? 289} icon="✅" color={GP.teal} bg={GP.tealLight} />
            <StatCard label="Deliveries Sent" value={stats?.total_deliveries ?? 34} icon="✉" color={GP.amber} bg={GP.amberLight} />
            <StatCard label="Total Photos" value={stats?.total_photos ?? 312} icon="📸" color={GP.coral} bg={GP.coralLight} />
          </div>

          {/* Charts row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* Bar chart */}
            <div style={{ background: GP.white, borderRadius: 16, padding: "20px 24px", boxShadow: GP.shadow1 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: GP.textPrimary }}>Photos per Month</h3>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 110 }}>
                {bars.map((b, i) => (
                  <div key={b.month} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                    <div style={{ fontSize: 10, color: GP.textTertiary, fontWeight: 500 }}>{b.count}</div>
                    <div style={{
                      width: "100%",
                      borderRadius: "5px 5px 0 0",
                      background: `linear-gradient(180deg, ${GP.blue}, ${GP.blueDark})`,
                      height: `${(b.count / maxCount) * 90}px`,
                      minHeight: 4,
                      transition: "height 0.8s ease",
                      animation: `fadeUp ${0.5 + i * 0.08}s ease both`,
                    }} />
                    <div style={{ fontSize: 10, color: GP.textTertiary }}>{b.month}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* People chart */}
            <div style={{ background: GP.white, borderRadius: 16, padding: "20px 24px", boxShadow: GP.shadow1 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: GP.textPrimary }}>Most Photographed</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {displayPeople.map(p => (
                  <div key={p.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 18, width: 24, textAlign: "center" }}>{p.emoji || "👤"}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyvalue: "space-between", marginBottom: 3 }}>
                        <span style={{ fontSize: 12, fontWeight: 500, color: GP.textPrimary }}>{p.name}</span>
                        <span style={{ fontSize: 11, color: GP.textTertiary }}>{p.photoCount || p.photo_count || 0}</span>
                      </div>
                      <ProgressBar value={Math.min(((p.photoCount || p.photo_count || 0) / Math.max(stats?.total_photos || 1, 50)) * 100, 100)} color={p.color || GP.blue} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
