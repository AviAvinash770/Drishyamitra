import React, { useState, useEffect, useCallback } from "react";
import { api } from "../../api";
import { GP } from "../../styles/theme";
import IconBtn from "../common/IconBtn";
import PhotoCard from "../gallery/PhotoCard";
import PhotoDetailModal from "../gallery/PhotoDetailModal";
import UploadModal from "../gallery/UploadModal";

export default function GalleryPage({
  showNotif,
  search,
  setSearch,
  setPage,
  setShareParams,
  refreshTrigger,
  filter,
  setFilter,
  setChatPreFill,
  addingToAlbum,
  setAddingToAlbum,
  setActivePhotoIds
}) {
  const [photos, setPhotos] = useState([]);
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [view, setView] = useState("grid");
  const [selectMode, setSelectMode] = useState(false);
  const [selectedPhotoIds, setSelectedPhotoIds] = useState([]);
  const [customAlbums, setCustomAlbums] = useState([]);

  useEffect(() => {
    api.albums.list().then(list => {
      // Filter out auto-generated "Scene:" albums and default event albums
      const filtered = list.filter(a => 
        !a.name.startsWith("Scene:") && 
        !["Birthdays", "Weddings", "Anniversaries"].includes(a.name)
      );
      setCustomAlbums(filtered);
    }).catch(err => console.error("Failed to load custom albums:", err));
  }, [refreshTrigger, addingToAlbum]);

  useEffect(() => {
    if (addingToAlbum) {
      setSelectMode(true);
      setSelectedPhotoIds([]);
    }
  }, [addingToAlbum]);

  const handleBulkAssign = async () => {
    const labelName = window.prompt(`Assign ${selectedPhotoIds.length} photos to which person?\n(Type an existing name or create a new one)`);
    if (!labelName || !labelName.trim()) return;
    
    try {
      await Promise.all(selectedPhotoIds.map(id => api.photos.assignLabel(id, labelName.trim())));
      showNotif(`Successfully assigned ${selectedPhotoIds.length} photos to ${labelName}`, "success");
      setSelectedPhotoIds([]);
      setSelectMode(false);
      loadData();
    } catch (err) {
      showNotif("Failed to assign photos.", "error");
    }
  };

  const handleSelectPhoto = (id) => {
    setSelectedPhotoIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleBulkDelete = async () => {
    if (window.confirm(`Are you sure you want to delete ${selectedPhotoIds.length} photos?`)) {
      try {
        await api.photos.deleteMultiple(selectedPhotoIds);
        showNotif(`Successfully deleted ${selectedPhotoIds.length} photos.`, "success");
        setSelectedPhotoIds([]);
        setSelectMode(false);
        loadData();
      } catch (err) {
        showNotif("Failed to delete selected photos.", "error");
      }
    }
  };

  const loadData = useCallback(async () => {
    try {
      const filters = {};
      if (search.trim()) filters.search = search.trim();
      
      if (filter === "Favourites") {
        filters.favorite = true;
      } else if (filter !== "All Photos") {
        filters.album = filter;
      }

      const list = await api.photos.list(filters);
      setPhotos(list);
    } catch (err) {
      showNotif("Failed to load photo gallery.", "error");
    }
  }, [filter, search, showNotif]);

  useEffect(() => {
    loadData();
  }, [loadData, refreshTrigger]);

  useEffect(() => {
    setSelectedPhotoIds([]);
  }, [filter, search]);

  useEffect(() => {
    if (setActivePhotoIds) {
      setActivePhotoIds(photos.map(p => p.id));
    }
  }, [photos, setActivePhotoIds]);

  const grouped = photos.reduce((acc, p) => {
    const month = p.date ? p.date.slice(0, 7) : "Unknown Date";
    if (!acc[month]) acc[month] = [];
    acc[month].push(p);
    return acc;
  }, {});

  const monthLabels = { "2025-01": "January 2025", "2025-02": "February 2025", "2025-03": "March 2025" };

  return (
    <div>
      {/* Adding to Album Banner */}
      {addingToAlbum && (
        <div style={{
          background: GP.blueLight,
          border: `1px solid ${GP.blue}`,
          borderRadius: 16,
          padding: "14px 20px",
          marginBottom: 20,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          boxShadow: GP.shadow1,
          animation: "fadeDown 0.2s ease"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>📂</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: GP.blue }}>
                Adding photos to album "{addingToAlbum.name}"
              </div>
              <div style={{ fontSize: 11, color: GP.textSecondary, marginTop: 2 }}>
                Select photos from your pool below and click "Add Selected" to save.
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={async () => {
                if (selectedPhotoIds.length === 0) {
                  showNotif("Please select at least one photo.", "warning");
                  return;
                }
                try {
                  await api.albums.assign(addingToAlbum.id, selectedPhotoIds);
                  showNotif(`Successfully added ${selectedPhotoIds.length} photo(s) to "${addingToAlbum.name}".`, "success");
                  setAddingToAlbum(null);
                  setSelectMode(false);
                  setSelectedPhotoIds([]);
                  loadData();
                } catch (err) {
                  console.error(err);
                  showNotif("Failed to add photos to album.", "error");
                }
              }}
              style={{
                background: GP.blue,
                color: "#fff",
                border: "none",
                borderRadius: 20,
                padding: "8px 18px",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: GP.shadow1,
              }}
            >
              Add Selected ({selectedPhotoIds.length})
            </button>
            <button
              onClick={() => {
                setAddingToAlbum(null);
                setSelectMode(false);
                setSelectedPhotoIds([]);
              }}
              style={{
                background: "#f1f3f4",
                color: GP.textPrimary,
                border: "none",
                borderRadius: 20,
                padding: "8px 18px",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: GP.shadow1,
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Flat Navigation Tabs */}
      <div style={{
        display: "flex",
        borderBottom: `1px solid ${GP.border}`,
        marginBottom: 20,
        gap: 24,
        overflowX: "auto",
        paddingBottom: 2
      }}>
        {[
          ["All Photos", "All Photos"],
          ["Favourites", "Favourites"],
          ["Birthdays", "Birthdays"],
          ["Weddings", "Weddings"],
          ["Anniversaries", "Anniversaries"],
          ...customAlbums.map(a => [a.name, a.name])
        ].map(([key, label]) => {
          const isActive = filter === key;
          return (
            <button
              key={key}
              onClick={() => setFilter(key)}
              style={{
                background: "none",
                border: "none",
                padding: "12px 4px",
                fontSize: 14,
                fontWeight: isActive ? 600 : 500,
                color: isActive ? GP.blue : GP.textSecondary,
                cursor: "pointer",
                borderBottom: isActive ? `3px solid ${GP.blue}` : "3px solid transparent",
                transition: "all 0.2s",
                whiteSpace: "nowrap",
                marginBottom: -3
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, flex: 1, color: GP.textPrimary }}>
          {selectMode ? `Selected ${selectedPhotoIds.length} photos` : "Photos"}
        </h2>
        <div style={{ display: "flex", gap: 6 }}>
          <IconBtn onClick={() => setView("grid")} title="Grid view">⊞</IconBtn>
          <IconBtn onClick={() => setView("masonry")} title="Masonry view">⊟</IconBtn>
        </div>
        {selectMode ? (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={handleBulkAssign}
              disabled={selectedPhotoIds.length === 0}
              style={{
                background: GP.blue,
                color: "#fff",
                border: "none",
                borderRadius: 20,
                padding: "8px 20px",
                fontSize: 13,
                fontWeight: 600,
                cursor: selectedPhotoIds.length === 0 ? "not-allowed" : "pointer",
                boxShadow: GP.shadow2,
                opacity: selectedPhotoIds.length === 0 ? 0.6 : 1,
              }}
            >
              Assign Person
            </button>
            <button
              onClick={handleBulkDelete}
              disabled={selectedPhotoIds.length === 0}
              style={{
                background: GP.coral,
                color: "#fff",
                border: "none",
                borderRadius: 20,
                padding: "8px 20px",
                fontSize: 13,
                fontWeight: 600,
                cursor: selectedPhotoIds.length === 0 ? "not-allowed" : "pointer",
                boxShadow: GP.shadow2,
                opacity: selectedPhotoIds.length === 0 ? 0.6 : 1,
              }}
            >
              Delete Selected
            </button>
            <button
              onClick={() => { setSelectMode(false); setSelectedPhotoIds([]); }}
              style={{
                background: "#dadce0",
                color: GP.textPrimary,
                border: "none",
                borderRadius: 20,
                padding: "8px 20px",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: GP.shadow1,
              }}
            >
              Cancel
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setSelectMode(true)}
              style={{
                background: "#f1f3f4",
                color: GP.textPrimary,
                border: "none",
                borderRadius: 20,
                padding: "8px 20px",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: GP.shadow1,
              }}
            >
              Select
            </button>
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
        )}
      </div>

      {/* Search Input only */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center" }}>
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
              <PhotoCard
                key={p.id}
                photo={p}
                onClick={() => setSelectedPhotoIndex(photos.indexOf(p))}
                selectMode={selectMode}
                selected={selectedPhotoIds.includes(p.id)}
                onSelect={handleSelectPhoto}
                onShareClick={() => {
                  if (setChatPreFill) {
                    setChatPreFill({
                      photoIds: [p.id],
                      message: "Share this photo via..."
                    });
                    setPage("chat");
                  }
                }}
              />
            ))}
          </div>
        </div>
      ))}

      {selectedPhotoIndex !== null && (
        <PhotoDetailModal
          photos={photos}
          currentIndex={selectedPhotoIndex}
          onIndexChange={setSelectedPhotoIndex}
          onClose={() => setSelectedPhotoIndex(null)}
          onDelete={async (id) => {
            try {
              await api.photos.delete(id);
              showNotif("Photo deleted successfully.", "success");
              setSelectedPhotoIndex(null);
              loadData();
            } catch (err) {
              showNotif("Failed to delete photo.", "error");
            }
          }}
          onShare={() => {
            setShareParams({ targetType: "photos", selectedPhotoIds: [photos[selectedPhotoIndex].id] });
            setPage("delivery");
            setSelectedPhotoIndex(null);
          }}
          onReLabel={async (photoId, newLabel) => {
            await loadData();
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
