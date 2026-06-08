import React from "react";
import { GP } from "../../styles/theme";

export default function Avatar({ person, size = 48 }) {
  return (
    <div style={{
      width: size,
      height: size,
      borderRadius: "50%",
      background: person.bg,
      color: person.color,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: size * 0.38,
      fontWeight: 700,
      flexShrink: 0,
      border: `2px solid ${GP.white}`,
      boxShadow: GP.shadow1,
    }}>
      {person.initials}
    </div>
  );
}
