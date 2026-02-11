import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

export const Scene1_Opening: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Typing effect for the question text
  const fullText = "AIを導入したい。";
  const fullText2 = "でも、どこから？";
  const charsToShow1 = Math.floor(
    interpolate(frame, [15, 60], [0, fullText.length], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    })
  );
  const charsToShow2 = Math.floor(
    interpolate(frame, [70, 110], [0, fullText2.length], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    })
  );

  // Cursor blink
  const cursorOpacity =
    frame < 120 ? (Math.floor(frame / 8) % 2 === 0 ? 1 : 0) : 0;

  // Background grid animation
  const gridOpacity = interpolate(frame, [0, 30], [0, 0.15], {
    extrapolateRight: "clamp",
  });

  // Fade out
  const fadeOut = interpolate(frame, [130, 150], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Floating particles
  const particles = Array.from({ length: 20 }, (_, i) => {
    const x = (i * 137.5) % 100;
    const baseY = (i * 73.7) % 100;
    const y = baseY - ((frame * 0.3 + i * 10) % 120);
    const size = 2 + (i % 3);
    const particleOpacity = interpolate(
      frame,
      [i * 3, i * 3 + 30],
      [0, 0.4],
      { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
    );
    return { x, y, size, opacity: particleOpacity };
  });

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      {/* Dark gradient background */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a0f 70%)",
        }}
      />

      {/* Animated grid */}
      <AbsoluteFill style={{ opacity: gridOpacity }}>
        {Array.from({ length: 20 }, (_, i) => (
          <div
            key={`h-${i}`}
            style={{
              position: "absolute",
              top: `${i * 5}%`,
              left: 0,
              right: 0,
              height: 1,
              background:
                "linear-gradient(90deg, transparent, rgba(100,130,255,0.3), transparent)",
              transform: `translateX(${Math.sin(frame * 0.02 + i) * 20}px)`,
            }}
          />
        ))}
        {Array.from({ length: 20 }, (_, i) => (
          <div
            key={`v-${i}`}
            style={{
              position: "absolute",
              left: `${i * 5}%`,
              top: 0,
              bottom: 0,
              width: 1,
              background:
                "linear-gradient(180deg, transparent, rgba(100,130,255,0.3), transparent)",
              transform: `translateY(${Math.sin(frame * 0.02 + i) * 20}px)`,
            }}
          />
        ))}
      </AbsoluteFill>

      {/* Floating particles */}
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            borderRadius: "50%",
            background: "#6488ff",
            opacity: p.opacity,
            boxShadow: `0 0 ${p.size * 3}px rgba(100,136,255,0.5)`,
          }}
        />
      ))}

      {/* Main text */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            fontSize: 72,
            color: "#e0e0e8",
            fontWeight: 300,
            letterSpacing: 4,
            lineHeight: 1.8,
            textAlign: "center",
          }}
        >
          <div>
            {fullText.slice(0, charsToShow1)}
            {frame < 70 && (
              <span style={{ opacity: cursorOpacity, color: "#6488ff" }}>
                |
              </span>
            )}
          </div>
          <div
            style={{
              fontSize: 80,
              fontWeight: 500,
              color: "#ffffff",
              marginTop: 10,
            }}
          >
            {fullText2.slice(0, charsToShow2)}
            {frame >= 70 && (
              <span style={{ opacity: cursorOpacity, color: "#6488ff" }}>
                |
              </span>
            )}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
