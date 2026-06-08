import React, { useState, useEffect, useCallback } from "react";
import { api } from "../../api";
import { GP } from "../../styles/theme";
import Chip from "../common/Chip";
import IconBtn from "../common/IconBtn";
import PhotoCard from "../gallery/PhotoCard";
import PhotoDetailModal from "../gallery/PhotoDetailModal";
import UploadModal from "../gallery/UploadModal";

export default function GalleryPage({ showNotif, search, setSearch, setPage, setShareParams }) {
  const [photos, setPhotos] = useState([]);
  const [filter, setFilter] = useState("All");
  const [selected, setSelected] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [view, setView] = useState("grid");
  const [albums, setAlbums] = useState([]);

  const loadData = useCallback(async () => {
    try {
      const filters = {};
      if (filter !== "All") filters.album = filter;
      if (search.trim()) filters.search = search.trim();
      const list = await api.photos.list(filters);
      setPhotos(list);

      const albumList = await api.albums.list();
      setAlbums(albumList);
    } catch (err) {
      showNotif("Failed to load photo gallery.", "error");
    }
  }, [filter, search, showNotif]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const folders = ["All", ...albums.map(f => f.name)];

  const grouped = photos.reduce((acc, p) => {
    const month = p.date ? p.date.slice(0, 7) : "Unknown Date";
    if (!acc[month]) acc[month] = [];
    acc[month].push(p);
    return acc;
  }, {});

  const monthLabels = { "2025-01": "January 2025", "2025-02": "February 2025", "2025-03": "March 2025" };

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, flex: 1, color: GP.textPrimary }}>Photos</h2>
        <div style={{ display: "flex", gap: 6 }}>
          <IconBtn onClick={() => setView("grid")} title="Grid view">⊞</IconBtn>
          <IconBtn onClick={() => setView("masonry")} title="Masonry view">⊟</IconBtn>
        </div>
        <button onClick={() => setShowUpload(true)} style={{
          background: GP.blue,
          color: "#fff",
          border: "none",
          borderRadius: 20,
          padding: "8px 20px",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 6,
          boxShadow: GP.shadow2,
        }}>+ Upload</button>
      </div>

      {/* Search + Filter chips */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: "0 0 260px" }}>
          <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: GP.textTertiary, fontSize: 16 }}>🔍</span>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by person or album…"
            style={{
              width: "100%",
              padding: "9px 14px 9px 38px",
              border: `1px solid ${GP.border}`,
              borderRadius: 24,
              fontSize: 13,
              background: GP.white,
              color: GP.textPrimary,
              transition: "all 0.15s",
              boxShadow: GP.shadow1,
            }}
            onFocus={e => e.target.style.borderColor = GP.blue}
            onBlur={e => e.target.style.borderColor = GP.border}
          />
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {folders.map(f => <Chip key={f} label={f} active={filter === f} onClick={() => setFilter(f)} />)}
        </div>
      </div>

      {/* Photo count */}
      <div style={{ fontSize: 13, color: GP.textTertiary, marginBottom: 16 }}>{photos.length} photos</div>

      {/* Timeline grouped grid */}
      {Object.entries(grouped).map(([month, monthPhotos]) => (
        <div key={month} style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: GP.textPrimary, marginBottom: 12 }}>
            {monthLabels[month] || month}
          </div>
          <div style={{
            display: "grid",
            gridTemplateColumns: view === "masonry"
              ? "repeat(auto-fill, minmax(160px, 1fr))"
              : "repeat(auto-fill, minmax(180px, 1fr))",
            gap: 10,
          }}>
            {monthPhotos.map(p => (
              <PhotoCard key={p.id} photo={p} onClick={() => setSelected(p)} />
            ))}
          </div>
        </div>
      ))}

      {selected && (
        <PhotoDetailModal
          photo={selected}
          onClose={() => setSelected(null)}
          onDelete={async (id) => {
            try {
              await api.photos.delete(id);
              showNotif("Photo deleted successfully.", "success");
              setSelected(null);
              loadData();
            } catch (err) {
              showNotif("Failed to delete photo.", "error");
            }
          }}
          onShare={() => {
            setShareParams({ targetType: "photos", selectedPhotoIds: [selected.id] });
            setPage("delivery");
            setSelected(null);
          }}
        />
      )}
      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onResult={() => {
            showNotif("Photo uploaded and indexed!", "success");
            setShowUpload(false);
            loadData();
          }}
        />
      )}
    </div>
  );
}
