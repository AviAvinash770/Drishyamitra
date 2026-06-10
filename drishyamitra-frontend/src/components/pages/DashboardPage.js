import React, { useState, useEffect } from "react";
import { api } from "../../api";
import { GP } from "../../styles/theme";
import PhotoCard from "../gallery/PhotoCard";
import PhotoDetailModal from "../gallery/PhotoDetailModal";
import PersonPhotosModal from "../gallery/PersonPhotosModal";

export default function DashboardPage({
  setPage,
  showNotif,
  onOpenAnalytics,
  setSearch,
  setShareParams,
  refreshTrigger,
  setChatPreFill,
  setGalleryFilter
}) {
  const [stats, setStats] = useState(null);
  const [persons, setPersons] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [recentPhotos, setRecentPhotos] = useState([]);
  const [loading, setLoading] = useState(true);

  // UI States
  const [localSearch, setLocalSearch] = useState("");
  const [viewingPerson, setViewingPerson] = useState(null);
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState(null);
  const [showScenesGrid, setShowScenesGrid] = useState(false);

  const loadDashboardData = async () => {
    try {
      const dashboardStats = await api.analytics.dashboard();
      setStats(dashboardStats);

      const peopleList = await api.faces.persons();
      setPersons(peopleList);

      const albumList = await api.albums.list();
      setAlbums(albumList);

      const photoList = await api.photos.list();
      // Keep only recent 8 photos for the dashboard
      setRecentPhotos(photoList.slice(0, 8));
    } catch (err) {
      console.error(err);
      showNotif("Failed to load dashboard data.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh", color: GP.textSecondary, fontSize: 14, fontWeight: 500 }}>
        Loading dashboard...
      </div>
    );
  }

  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    if (localSearch.trim()) {
      setSearch(localSearch.trim());
      setPage("gallery");
    }
  };

  const handleSuggestionClick = (query) => {
    setSearch(query);
    setPage("gallery");
  };

  const aiSuggestions = [
    "Photos of Priya at weddings",
    "Show photos of Avinash",
    "Greenery & Nature scenes",
    "Group photos from last week"
  ];

  // Filters automated Place & Scene albums
  const sceneAlbums = albums.filter(a => a.name.startswith?.("Scene:") || a.name.includes?.("Scene:"));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      {/* 1. TOP: Spacious Search Bar with AI Prompt Suggestions */}
      <section style={{
        background: GP.white,
        borderRadius: 24,
        padding: "28px 32px",
        boxShadow: GP.shadow1,
        border: `1px solid ${GP.borderLight}`,
        display: "flex",
        flexDirection: "column",
        gap: 16
      }}>
        <form onSubmit={handleSearchSubmit} style={{ position: "relative", width: "100%" }}>
          <span style={{ position: "absolute", left: 20, top: "50%", transform: "translateY(-50%)", color: GP.textTertiary, fontSize: 22 }}>🔍</span>
          <input
            placeholder='Ask or search anything... "beaches with Avinash" or "family photos"'
            value={localSearch}
            onChange={e => setLocalSearch(e.target.value)}
            style={{
              width: "100%",
              padding: "16px 24px 16px 56px",
              border: `1px solid ${GP.border}`,
              borderRadius: 30,
              fontSize: 16,
              background: GP.surface,
              color: GP.textPrimary,
              outline: "none",
              boxShadow: GP.shadow1,
              transition: "all 0.2s"
            }}
            onFocus={e => { e.target.style.background = GP.white; e.target.style.borderColor = GP.blue; e.target.style.boxShadow = GP.shadow2; }}
            onBlur={e => { e.target.style.background = GP.surface; e.target.style.borderColor = GP.border; e.target.style.boxShadow = GP.shadow1; }}
          />
          <button type="submit" style={{
            position: "absolute",
            right: 12,
            top: "50%",
            transform: "translateY(-50%)",
            background: GP.blue,
            color: GP.white,
            border: "none",
            borderRadius: 20,
            padding: "8px 18px",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            boxShadow: GP.shadow1,
            transition: "background 0.2s"
          }}
            onMouseEnter={e => e.currentTarget.style.background = "#1557b0"}
            onMouseLeave={e => e.currentTarget.style.background = GP.blue}
          >
            Search
          </button>
        </form>

        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: GP.textTertiary, fontWeight: 600 }}>💡 Try asking:</span>
          {aiSuggestions.map(s => (
            <button
              key={s}
              onClick={() => handleSuggestionClick(s)}
              style={{
                background: GP.surface,
                border: `1px solid ${GP.borderLight}`,
                borderRadius: 16,
                padding: "6px 14px",
                fontSize: 12,
                color: GP.textSecondary,
                cursor: "pointer",
                transition: "all 0.15s"
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = GP.blue; e.currentTarget.style.color = GP.blue; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = GP.borderLight; e.currentTarget.style.color = GP.textSecondary; }}
            >
              "{s}"
            </button>
          ))}
        </div>
      </section>

      {/* 2. MIDDLE: People Row (Horizontal Scrolling) */}
      <section>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: GP.textPrimary, marginBottom: 14 }}>People in Your Library</h3>
        <div style={{
          display: "flex",
          gap: 16,
          overflowX: "auto",
          padding: "4px 4px 12px 4px",
          scrollbarWidth: "thin"
        }}>
          {persons.map(p => (
            <div
              key={p.id}
              onClick={() => setViewingPerson(p)}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 8,
                cursor: "pointer",
                flexShrink: 0
              }}
            >
              <div style={{
                width: 76,
                height: 76,
                borderRadius: "50%",
                overflow: "hidden",
                border: `2px solid ${GP.border}`,
                boxShadow: GP.shadow1,
                transition: "all 0.2s",
                background: p.bg || GP.surface,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 28
              }}
                onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.06)"; e.currentTarget.style.borderColor = GP.blue; }}
                onMouseLeave={e => { e.currentTarget.style.transform = "scale(1)"; e.currentTarget.style.borderColor = GP.border; }}
              >
                {p.photo_url ? (
                  <img src={p.photo_url} alt={p.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  p.emoji || "👤"
                )}
              </div>
              <span style={{ fontSize: 12, fontWeight: 500, color: GP.textPrimary }}>{p.name}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 3. MIDDLE BOTTOM: Smart Albums Row */}
      <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: GP.textPrimary, marginBottom: 4 }}>Smart Categories</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          {/* Favorites Card */}
          <div
            onClick={() => { if (setGalleryFilter) setGalleryFilter("Favourites"); setPage("gallery"); }}
            style={{
              background: GP.white,
              borderRadius: 16,
              padding: "16px 20px",
              border: `1px solid ${GP.borderLight}`,
              boxShadow: GP.shadow1,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 16,
              transition: "transform 0.2s"
            }}
            onMouseEnter={e => e.currentTarget.style.transform = "translateY(-3px)"}
            onMouseLeave={e => e.currentTarget.style.transform = "none"}
          >
            <div style={{ width: 44, height: 44, borderRadius: 12, background: "#fce8e6", display: "flex", alignItems: "center", justifyvalue: "center", justifyContent: "center", fontSize: 22 }}>❤️</div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: GP.textPrimary }}>Favorites</span>
              <span style={{ fontSize: 12, color: GP.textTertiary, marginTop: 2 }}>{stats?.total_favorites ?? 0} photos</span>
            </div>
          </div>

          {/* Scenes Card */}
          <div
            onClick={() => setShowScenesGrid(!showScenesGrid)}
            style={{
              background: showScenesGrid ? GP.blueLight : GP.white,
              borderRadius: 16,
              padding: "16px 20px",
              border: `1px solid ${showScenesGrid ? GP.blue : GP.borderLight}`,
              boxShadow: GP.shadow1,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 16,
              transition: "transform 0.2s"
            }}
            onMouseEnter={e => e.currentTarget.style.transform = "translateY(-3px)"}
            onMouseLeave={e => e.currentTarget.style.transform = "none"}
          >
            <div style={{ width: 44, height: 44, borderRadius: 12, background: "#e6f4ea", display: "flex", alignItems: "center", justifyvalue: "center", justifyContent: "center", fontSize: 22 }}>🌄</div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: GP.textPrimary }}>Places & Scenes</span>
              <span style={{ fontSize: 12, color: GP.textTertiary, marginTop: 2 }}>{stats?.total_scenes_albums ?? 0} scene albums</span>
            </div>
          </div>

          {/* Group Photos Card */}
          <div
            onClick={() => { setSearch("group"); setPage("gallery"); }}
            style={{
              background: GP.white,
              borderRadius: 16,
              padding: "16px 20px",
              border: `1px solid ${GP.borderLight}`,
              boxShadow: GP.shadow1,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 16,
              transition: "transform 0.2s"
            }}
            onMouseEnter={e => e.currentTarget.style.transform = "translateY(-3px)"}
            onMouseLeave={e => e.currentTarget.style.transform = "none"}
          >
            <div style={{ width: 44, height: 44, borderRadius: 12, background: "#e8f0fe", display: "flex", alignItems: "center", justifyvalue: "center", justifyContent: "center", fontSize: 22 }}>👥</div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: GP.textPrimary }}>Group Photos</span>
              <span style={{ fontSize: 12, color: GP.textTertiary, marginTop: 2 }}>{stats?.total_group_photos ?? 0} photos</span>
            </div>
          </div>
        </div>

        {/* Places & Scenes sub-grid */}
        {showScenesGrid && (
          <div style={{
            background: GP.white,
            borderRadius: 16,
            padding: 20,
            border: `1px solid ${GP.blue}`,
            boxShadow: GP.shadow1,
            animation: "fadeUp 0.2s ease",
            display: "flex",
            flexDirection: "column",
            gap: 12
          }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: GP.blue }}>Auto-Grouped Scenes:</span>
            {sceneAlbums.length === 0 ? (
              <span style={{ fontSize: 12, color: GP.textTertiary }}>No auto-grouped scenes found yet. Upload more photos to trigger clustering!</span>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12 }}>
                {sceneAlbums.map(sa => (
                  <div
                    key={sa.id}
                    onClick={() => { setSearch(sa.name); setPage("gallery"); }}
                    style={{
                      padding: "8px 12px",
                      background: sa.bg,
                      borderRadius: 12,
                      cursor: "pointer",
                      border: `1px solid ${sa.color}`,
                      display: "flex",
                      flexDirection: "column",
                      gap: 4
                    }}
                  >
                    <span style={{ fontSize: 14 }}>{sa.icon || "📂"}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: sa.color }}>{sa.name.replace("Scene: ", "")}</span>
                    <span style={{ fontSize: 10, color: GP.textTertiary }}>{sa.count} photos</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* 4. BOTTOM: Recent Photos Staggered Masonry Grid */}
      <section>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: GP.textPrimary, marginBottom: 14 }}>Recent Photos</h3>
        {recentPhotos.length === 0 ? (
          <div style={{ background: GP.white, borderRadius: 16, padding: 40, textAlign: "center", color: GP.textTertiary, border: `1px solid ${GP.borderLight}`, boxShadow: GP.shadow1 }}>
            <span style={{ fontSize: 32 }}>📸</span>
            <p style={{ fontSize: 13, marginTop: 8 }}>Your photo library is empty. Upload your first photo to get started!</p>
          </div>
        ) : (
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: 14,
            alignItems: "start"
          }}>
            {recentPhotos.map(p => (
              <PhotoCard
                key={p.id}
                photo={p}
                onClick={() => setSelectedPhotoIndex(recentPhotos.indexOf(p))}
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
        )}
      </section>

      {/* Modal Overlays */}
      {viewingPerson && (
        <PersonPhotosModal
          person={viewingPerson}
          onClose={() => setViewingPerson(null)}
          showNotif={showNotif}
        />
      )}

      {selectedPhotoIndex !== null && (
        <PhotoDetailModal
          photos={recentPhotos}
          currentIndex={selectedPhotoIndex}
          onIndexChange={setSelectedPhotoIndex}
          onClose={() => setSelectedPhotoIndex(null)}
          onDelete={async (id) => {
            try {
              await api.photos.delete(id);
              showNotif("Photo deleted successfully.", "success");
              setSelectedPhotoIndex(null);
              loadDashboardData();
            } catch (err) {
              showNotif("Failed to delete photo.", "error");
            }
          }}
          onShare={() => {
            setShareParams({ targetType: "photos", selectedPhotoIds: [recentPhotos[selectedPhotoIndex].id] });
            setPage("delivery");
            setSelectedPhotoIndex(null);
          }}
          onReLabel={async (photoId, newLabel) => {
            await loadDashboardData();
          }}
        />
      )}
    </div>
  );
}
