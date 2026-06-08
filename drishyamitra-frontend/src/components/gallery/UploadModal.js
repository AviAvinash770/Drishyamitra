import React, { useState, useRef } from "react";
import { api } from "../../api";
import { GP } from "../../styles/theme";
import IconBtn from "../common/IconBtn";
import Spinner from "../common/Spinner";
import ProgressBar from "../common/ProgressBar";

export default function UploadModal({ onClose, onResult }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null); // { current: 1, total: 3, name: "img.jpg" }
  const fileRef = useRef();

  const themes = [
    { label: "Family gathering at festival", emoji: "🎉" },
    { label: "Wedding ceremony outdoors", emoji: "💍" },
    { label: "Birthday party with cake", emoji: "🎂" },
    { label: "Vacation beach sunset", emoji: "🌅" },
    { label: "Corporate event headshots", emoji: "📸" },
  ];

  async function analyze(desc) {
    setAnalyzing(true);
    try {
      await new Promise(r => setTimeout(r, 1200));
      setResult({
        description: `Theme test analysis: ${desc}`,
        faces: ["Priya Sharma"],
        folder: "Events",
        tags: ["auto-tagged", "2025"],
        confidence: 0.87
      });
    } catch {
      setResult({ description: "Photo processed and indexed.", faces: ["Priya Sharma"], folder: "Events", tags: ["auto-tagged", "2025"], confidence: 0.87 });
    } finally { setAnalyzing(false); }
  }

  async function handleMultipleUploads(files) {
    setAnalyzing(true);
    setUploadProgress({ current: 1, total: files.length, name: files[0].name });

    let successCount = 0;
    let failedCount = 0;
    let lastResult = null;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setUploadProgress({ current: i + 1, total: files.length, name: file.name });
      try {
        const res = await api.photos.upload(file);
        successCount++;
        lastResult = {
          name: file.name,
          description: res.description || "Photo processed and indexed.",
          faces: res.persons || [],
          folder: res.folder || "Events",
          tags: res.tags || [],
          confidence: res.analysis?.confidence || 0.95
        };
      } catch (err) {
        console.error(err);
        failedCount++;
      }
    }

    setUploadProgress(null);
    setAnalyzing(false);

    if (successCount > 0) {
      if (files.length === 1 && lastResult) {
        setResult(lastResult);
      } else {
        setResult({
          isSummary: true,
          message: `Successfully uploaded and analyzed ${successCount} photo(s).`,
          description: `All ${successCount} photos have been indexed and categorized by the AI system.` + (failedCount > 0 ? ` (${failedCount} failed to upload)` : ""),
          faces: [],
          folder: "Multiple",
          tags: ["bulk-upload", `${successCount} photos`],
          confidence: 0.95
        });
      }
      onResult();
    } else {
      alert("Failed to upload photos.");
    }
  }

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()} style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.6)",
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
        maxWidth: 500,
        maxHeight: "90vh",
        overflowY: "auto",
        animation: "scaleIn 0.25s cubic-bezier(0.34,1.56,0.64,1)",
      }}>
        <div style={{ display: "flex", alignItems: "center", padding: "16px 20px", borderBottom: `1px solid ${GP.border}` }}>
          <span style={{ flex: 1, fontSize: 16, fontWeight: 600 }}>Upload & AI Analyze</span>
          <IconBtn onClick={onClose}>✕</IconBtn>
        </div>

        <div style={{ padding: 24 }}>
          {!result ? (
            <>
              {/* Drop zone */}
              <div
                className="upload-zone"
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={e => {
                  e.preventDefault();
                  setDragging(false);
                  const f = Array.from(e.dataTransfer.files);
                  if (f.length > 0) { handleMultipleUploads(f); }
                }}
                onClick={() => fileRef.current?.click()}
                style={{
                  border: `2px dashed ${dragging ? GP.blue : GP.border}`,
                  borderRadius: 16,
                  padding: "40px 24px",
                  textAlign: "center",
                  cursor: "pointer",
                  transition: "all 0.2s",
                  background: dragging ? GP.blueLight : GP.surface,
                  marginBottom: 20,
                }}
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  multiple
                  style={{ display: "none" }}
                  onChange={e => {
                    const f = Array.from(e.target.files);
                    if (f.length > 0) { handleMultipleUploads(f); }
                  }}
                />
                <div style={{ fontSize: 40, marginBottom: 12 }}>📁</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: GP.textPrimary, marginBottom: 6 }}>
                  Drag photos here or click to browse
                </div>
                <div style={{ fontSize: 13, color: GP.textTertiary }}>JPG, PNG, HEIC up to 50MB (multiple allowed)</div>
              </div>

              {!analyzing && (
                <>
                  <div style={{ fontSize: 12, color: GP.textTertiary, fontWeight: 500, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>Test AI Analysis</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {themes.map(t => (
                      <button key={t.label} disabled={analyzing} onClick={() => analyze(t.label)} style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        padding: "12px 16px",
                        background: GP.surface,
                        border: `1px solid ${GP.border}`,
                        borderRadius: 12,
                        cursor: "pointer",
                        fontSize: 13,
                        color: GP.textPrimary,
                        textAlign: "left",
                        transition: "all 0.15s",
                      }}
                        onMouseEnter={e => e.currentTarget.style.background = GP.blueLight}
                        onMouseLeave={e => e.currentTarget.style.background = GP.surface}
                      >
                        <span style={{ fontSize: 20 }}>{t.emoji}</span>
                        <span style={{ flex: 1 }}>{t.label}</span>
                        <span style={{ color: GP.textTertiary }}>→</span>
                      </button>
                    ))}
                  </div>
                </>
              )}

              {analyzing && (
                <div style={{ textAlign: "center", padding: "24px 0" }}>
                  <Spinner />
                  <div style={{ fontSize: 13, color: GP.blue, marginTop: 12, fontWeight: 500 }}>
                    {uploadProgress 
                      ? `Uploading ${uploadProgress.current} of ${uploadProgress.total}…`
                      : "Analyzing with DeepFace & Claude AI…"}
                  </div>
                  {uploadProgress && (
                    <div style={{ fontSize: 11, color: GP.textSecondary, marginTop: 4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      Processing: {uploadProgress.name}
                    </div>
                  )}
                  <div style={{ marginTop: 12 }}>
                    <ProgressBar value={uploadProgress ? (uploadProgress.current / uploadProgress.total) * 100 : 70} />
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 16, animation: "fadeUp 0.3s" }}>
              <div style={{ background: GP.greenLight, border: `1px solid ${GP.green}30`, borderRadius: 12, padding: "16px 18px" }}>
                <div style={{ color: GP.green, fontWeight: 600, fontSize: 13, marginBottom: 6 }}>✓ {result.isSummary ? "Bulk Upload Complete" : "AI Analysis Complete"}</div>
                <div style={{ fontSize: 13, color: GP.textPrimary, lineHeight: 1.6 }}>{result.description || result.message}</div>
              </div>

              {!result.isSummary && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <div style={{ background: GP.surface, borderRadius: 12, padding: "14px 16px" }}>
                      <div style={{ fontSize: 11, color: GP.textTertiary, fontWeight: 500, marginBottom: 6 }}>Detected Faces</div>
                      {result.faces && result.faces.length > 0 ? (
                        result.faces.map(f => <div key={f} style={{ fontSize: 13, color: GP.textPrimary, fontWeight: 500 }}>👤 {f}</div>)
                      ) : (
                        <div style={{ fontSize: 12, color: GP.textSecondary }}>No faces detected</div>
                      )}
                    </div>
                    <div style={{ background: GP.surface, borderRadius: 12, padding: "14px 16px" }}>
                      <div style={{ fontSize: 11, color: GP.textTertiary, fontWeight: 500, marginBottom: 6 }}>Folder & Confidence</div>
                      <div style={{ fontSize: 13, color: GP.blue, fontWeight: 600 }}>📁 {result.folder}</div>
                      <div style={{ fontSize: 12, color: GP.green, marginTop: 4 }}>{Math.round((result.confidence || 0.9) * 100)}% confidence</div>
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: 11, color: GP.textTertiary, fontWeight: 500, marginBottom: 8 }}>Auto-generated Tags</div>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {result.tags?.map(t => (
                        <span key={t} style={{ padding: "4px 12px", borderRadius: 20, background: GP.blueLight, color: GP.blue, fontSize: 12, fontWeight: 500 }}>{t}</span>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {result.isSummary && (
                <div style={{ background: GP.surface, borderRadius: 12, padding: "16px", display: "flex", flexDirection: "column", gap: 8 }}>
                  <div style={{ fontSize: 13, color: GP.textPrimary, fontWeight: 500 }}>{result.message}</div>
                  <div style={{ fontSize: 12, color: GP.textSecondary }}>All successfully uploaded photos are now organized in your smart albums and indexed for semantic search query support.</div>
                </div>
              )}

              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => { onClose(); }} style={{
                  flex: 1,
                  padding: "12px",
                  borderRadius: 12,
                  background: GP.blue,
                  color: "#fff",
                  border: "none",
                  cursor: "pointer",
                  fontSize: 14,
                  fontWeight: 600,
                  transition: "background 0.15s",
                }}
                  onMouseEnter={e => e.currentTarget.style.background = GP.blueDark}
                  onMouseLeave={e => e.currentTarget.style.background = GP.blue}
                >Return to Gallery</button>
                <button onClick={() => setResult(null)} style={{
                  padding: "12px 20px",
                  borderRadius: 12,
                  background: GP.surface,
                  border: `1px solid ${GP.border}`,
                  cursor: "pointer",
                  fontSize: 14,
                  fontWeight: 500,
                  color: GP.textPrimary,
                }}>Upload More</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
