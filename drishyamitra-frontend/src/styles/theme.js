export const GP = {
  // Base surfaces — Slate Obsidian
  white: "#ffffff",
  surface: "#f8fafc",               // Slate 50 — main page background
  surfaceElevated: "#ffffff",
  containerDark: "#0f172a",         // Slate 900 — dark mode containers / sidebar
  containerMid: "#1e293b",          // Slate 800 — section headers, cards on dark bg

  // Borders
  border: "#e2e8f0",                // Slate 200
  borderLight: "#f1f5f9",           // Slate 100

  // Typography
  textPrimary: "#1e293b",           // Slate 800 — primary headers & body
  textSecondary: "#475569",         // Slate 600
  textTertiary: "#94a3b8",          // Slate 400

  // Accent — Cyan (replaces old blue)
  blue: "#06b6d4",                  // Cyan 500 — primary actions, badges, links
  blueLight: "#e0f7fa",             // Cyan 50 — hover fills, chip backgrounds
  blueDark: "#0891b2",              // Cyan 600 — pressed / hover states

  // Supporting palette
  teal: "#14b8a6",                  // Teal 500
  tealLight: "#ccfbf1",             // Teal 100
  coral: "#f43f5e",                 // Rose 500
  coralLight: "#ffe4e6",            // Rose 100
  amber: "#f59e0b",                 // Amber 500
  amberLight: "#fef3c7",            // Amber 100
  green: "#22c55e",                 // Green 500
  greenLight: "#dcfce7",            // Green 100
  purple: "#a855f7",                // Purple 500
  purpleLight: "#f3e8ff",           // Purple 100

  // Shadows
  shadow1: "0 1px 2px rgba(15,23,42,0.08), 0 1px 3px rgba(15,23,42,0.06)",
  shadow2: "0 2px 6px rgba(15,23,42,0.12), 0 1px 2px rgba(15,23,42,0.08)",
  shadow3: "0 4px 12px rgba(15,23,42,0.12), 0 2px 4px rgba(15,23,42,0.08)",
  shadowHover: "0 8px 24px rgba(15,23,42,0.16), 0 2px 8px rgba(15,23,42,0.10)",
};

export const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Google+Sans+Text:wght@400;500&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Google Sans Text', 'Google Sans', 'Roboto', sans-serif; background: ${GP.surface}; color: ${GP.textPrimary}; }
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
  input, select, textarea, button { font-family: inherit; }
  input:focus, select:focus, textarea:focus { outline: none; }

  @keyframes fadeUp { from { opacity:0; transform: translateY(12px); } to { opacity:1; transform: translateY(0); } }
  @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
  @keyframes scaleIn { from { opacity:0; transform: scale(0.95); } to { opacity:1; transform: scale(1); } }
  @keyframes slideRight { from { opacity:0; transform: translateX(-8px); } to { opacity:1; transform: translateX(0); } }
  @keyframes notifSlide { from { opacity:0; transform: translateX(24px); } to { opacity:1; transform: translateX(0); } }
  @keyframes ripple { to { transform: scale(4); opacity: 0; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

  .photo-card:hover .photo-overlay { opacity: 1 !important; }
  .photo-card:hover .photo-check { opacity: 1 !important; }
  .sidebar-item:hover { background: ${GP.blueLight} !important; }
  .sidebar-item:hover .sidebar-icon { color: ${GP.blue} !important; }
  .nav-tab:hover { background: rgba(6,182,212,0.08) !important; }
  .chip:hover { background: #e2e8f0 !important; }
  .chip-active { background: ${GP.blueLight} !important; color: ${GP.blue} !important; border-color: ${GP.blue} !important; }
  .action-btn:hover { box-shadow: ${GP.shadowHover} !important; transform: translateY(-1px) !important; }
  .person-card:hover { box-shadow: ${GP.shadowHover} !important; transform: translateY(-2px) !important; }
  .folder-row:hover { background: ${GP.blueLight} !important; border-radius: 8px; }
  .fab { position: fixed; bottom: 28px; right: 28px; width: 56px; height: 56px; border-radius: 16px; background: ${GP.blue}; color: #fff; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: ${GP.shadow3}; transition: all 0.2s; z-index: 50; }
  .fab:hover { background: ${GP.blueDark}; box-shadow: ${GP.shadowHover}; transform: translateY(-2px) scale(1.04); }
  .upload-zone:hover { border-color: ${GP.blue} !important; background: ${GP.blueLight} !important; }
  .quick-action:hover { box-shadow: ${GP.shadowHover} !important; transform: translateY(-2px) !important; }
  .memory-card:hover { box-shadow: ${GP.shadowHover} !important; transform: scale(1.02) !important; }
  .send-btn:hover:not(:disabled) { background: ${GP.blueDark} !important; }
  .icon-btn:hover { background: rgba(15,23,42,0.06) !important; }
  .stat-chip:hover { box-shadow: ${GP.shadow2} !important; }
  select option { background: ${GP.white}; color: ${GP.textPrimary}; }
`;
