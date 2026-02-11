import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

export const Scene6_Ending: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo animation
  const logoSpring = spring({
    frame: frame - 5,
    fps,
    config: { damping: 12, stiffness: 80 },
  });
  const logoScale = interpolate(logoSpring, [0, 1], [1.3, 1]);
  const logoOpacity = interpolate(logoSpring, [0, 1], [0, 1]);

  // Subtitle
  const subtitleOpacity = interpolate(frame, [20, 35], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // CTA
  const ctaOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const ctaY = interpolate(frame, [40, 55], [20, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Background pulse
  const pulseBrightness = interpolate(
    Math.sin(frame * 0.08),
    [-1, 1],
    [0.8, 1.2]
  );

  // Particle constellation
  const particles = Array.from({ length: 30 }, (_, i) => {
    const angle = (i / 30) * Math.PI * 2;
    const radius = 350 + Math.sin(frame * 0.02 + i * 0.5) * 30;
    return {
      x: 960 + Math.cos(angle + frame * 0.005) * radius,
      y: 540 + Math.sin(angle + frame * 0.005) * radius,
      size: 2 + (i % 3),
      opacity: 0.2 + Math.sin(frame * 0.05 + i) * 0.15,
    };
  });

  return (
    <AbsoluteFill>
      {/* Background */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, #0d1b3e 0%, #0a0a0f 60%)",
        }}
      />

      {/* Particle ring */}
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: p.x,
            top: p.y,
            width: p.size,
            height: p.size,
            borderRadius: "50%",
            background: "#6488ff",
            opacity: p.opacity * logoOpacity,
            boxShadow: "0 0 10px rgba(100,136,255,0.5)",
          }}
        />
      ))}

      {/* Connecting lines between nearby particles */}
      <svg
        width={1920}
        height={1080}
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        {particles.map((p1, i) =>
          particles.slice(i + 1).map((p2, j) => {
            const dist = Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2);
            if (dist < 150) {
              return (
                <line
                  key={`${i}-${j}`}
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  stroke="rgba(100,136,255,0.1)"
                  strokeWidth={1}
                  opacity={logoOpacity}
                />
              );
            }
            return null;
          })
        )}
      </svg>

      {/* Main content */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
        }}
      >
        {/* Logo */}
        <div
          style={{
            transform: `scale(${logoScale})`,
            opacity: logoOpacity,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontSize: 140,
              fontWeight: 800,
              color: "#ffffff",
              letterSpacing: -4,
              textShadow:
                "0 0 40px rgba(100,136,255,0.6), 0 0 80px rgba(100,136,255,0.3)",
            }}
          >
            int.
          </div>
        </div>

        {/* Subtitle */}
        <div style={{ opacity: subtitleOpacity, marginBottom: 40 }}>
          <div
            style={{
              fontSize: 32,
              color: "#8899cc",
              fontWeight: 400,
              letterSpacing: 6,
            }}
          >
            AI-Native Incubation Partner
          </div>
        </div>

        {/* Tagline */}
        <div
          style={{
            opacity: ctaOpacity,
            transform: `translateY(${ctaY}px)`,
          }}
        >
          <div
            style={{
              fontSize: 48,
              color: "#ffffff",
              fontWeight: 600,
              letterSpacing: 8,
              textShadow: "0 0 20px rgba(100,136,255,0.4)",
            }}
          >
            構想を、実装する。
          </div>
        </div>

        {/* URL */}
        <div
          style={{
            opacity: ctaOpacity,
            marginTop: 50,
          }}
        >
          <div
            style={{
              fontSize: 22,
              color: "#556688",
              fontWeight: 400,
              letterSpacing: 3,
              padding: "10px 30px",
              borderRadius: 30,
              border: "1px solid rgba(100,136,255,0.2)",
              background: "rgba(100,136,255,0.05)",
            }}
          >
            llm-new-site.vercel.app
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
