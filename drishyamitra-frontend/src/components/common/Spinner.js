import React from "react";
import { GP } from "../../styles/theme";

export default function Spinner() {
  return (
    <div style={{
      width: 20,
      height: 20,
      borderRadius: "50%",
      border: `2px solid ${GP.border}`,
      borderTopColor: GP.blue,
      animation: "spin 0.7s linear infinite",
      display: "inline-block",
    }} />
  );
}
