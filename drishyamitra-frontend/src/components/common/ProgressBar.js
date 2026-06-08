import React from "react";
import { GP } from "../../styles/theme";

export default function ProgressBar({ value, color }) {
  return (
    <div style={{ height: 4, background: GP.borderLight, borderRadius: 2, overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${value}%`, background: color || GP.blue, borderRadius: 2, transition: "width 0.6s ease" }} />
    </div>
  );
}
