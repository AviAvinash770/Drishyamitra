export const GP = {
  white: "#ffffff",
  surface: "#f8f9fa",
  surfaceElevated: "#ffffff",
  border: "#e8eaed",
  borderLight: "#f1f3f4",
  textPrimary: "#202124",
  textSecondary: "#5f6368",
  textTertiary: "#9aa0a6",
  blue: "#1a73e8",
  blueLight: "#e8f0fe",
  blueDark: "#1557b0",
  teal: "#00897b",
  tealLight: "#e0f2f1",
  coral: "#e8453c",
  coralLight: "#fce8e6",
  amber: "#f9ab00",
  amberLight: "#fef7e0",
  green: "#34a853",
  greenLight: "#e6f4ea",
  purple: "#9334e6",
  purpleLight: "#f3e8fd",
  shadow1: "0 1px 2px rgba(60,64,67,0.1), 0 1px 3px rgba(60,64,67,0.08)",
  shadow2: "0 2px 6px rgba(60,64,67,0.15), 0 1px 2px rgba(60,64,67,0.1)",
  shadow3: "0 4px 12px rgba(60,64,67,0.15), 0 2px 4px rgba(60,64,67,0.1)",
  shadowHover: "0 8px 24px rgba(60,64,67,0.2), 0 2px 8px rgba(60,64,67,0.12)",
};

export const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Google+Sans+Text:wght@400;500&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Google Sans Text', 'Google Sans', 'Roboto', sans-serif; background: ${GP.surface}; color: ${GP.textPrimary}; }
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #dadce0; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #bdc1c6; }
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
  .nav-tab:hover { background: rgba(26,115,232,0.08) !important; }
  .chip:hover { background: #dadce0 !important; }
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
  .icon-btn:hover { background: rgba(32,33,36,0.08) !important; }
  .stat-chip:hover { box-shadow: ${GP.shadow2} !important; }
  select option { background: ${GP.white}; color: ${GP.textPrimary}; }
`;
