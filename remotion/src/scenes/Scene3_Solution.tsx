import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

export const Scene3_Solution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo reveal animation
  const logoSpring = spring({
    frame: frame - 10,
    fps,
    config: { damping: 10, stiffness: 60 },
  });
  const logoScale = interpolate(logoSpring, [0, 1], [0, 1]);
  const logoOpacity = interpolate(logoSpring, [0, 1], [0, 1]);

  // Tagline animation
  const taglineSpring = spring({
    frame: frame - 50,
    fps,
    config: { damping: 12, stiffness: 80 },
  });
  const taglineOpacity = interpolate(taglineSpring, [0, 1], [0, 1]);
  const taglineY = interpolate(taglineSpring, [0, 1], [40, 0]);

  // Subtitle animation
  const subtitleOpacity = interpolate(frame, [80, 100], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Light burst effect
  const burstScale = interpolate(frame, [10, 50], [0, 3], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const burstOpacity = interpolate(frame, [10, 50], [0.6, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Fade out
  const fadeOut = interpolate(frame, [130, 150], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Rotating rays
  const rayRotation = frame * 0.3;

  // Glowing orbs
  const orbs = Array.from({ length: 6 }, (_, i) => {
    const angle = (i / 6) * Math.PI * 2 + frame * 0.01;
    const radius = 300 + Math.sin(frame * 0.03 + i) * 50;
    return {
      x: 960 + Math.cos(angle) * radius,
      y: 540 + Math.sin(angle) * radius,
      opacity: interpolate(frame, [20, 50], [0, 0.4], {
        extrapolateRight: "clamp",
        extrapolateLeft: "clamp",
      }),
    };
  });

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      {/* Background */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, #0d1b3e 0%, #0a0a0f 60%)",
        }}
      />

      {/* Light burst */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          width: 200,
          height: 200,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(100,136,255,0.8), transparent 70%)",
          transform: `translate(-50%, -50%) scale(${burstScale})`,
          opacity: burstOpacity,
        }}
      />

      {/* Rotating light rays */}
      {Array.from({ length: 8 }, (_, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            width: 2,
            height: 600,
            background:
              "linear-gradient(180deg, rgba(100,136,255,0.15), transparent)",
            transformOrigin: "top center",
            transform: `translate(-50%, 0) rotate(${rayRotation + i * 45}deg)`,
            opacity: interpolate(frame, [20, 50], [0, 1], {
              extrapolateRight: "clamp",
              extrapolateLeft: "clamp",
            }),
          }}
        />
      ))}

      {/* Glowing orbs */}
      {orbs.map((orb, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: orb.x - 15,
            top: orb.y - 15,
            width: 30,
            height: 30,
            borderRadius: "50%",
            background: "#6488ff",
            opacity: orb.opacity,
            boxShadow: "0 0 40px rgba(100,136,255,0.6)",
            filter: "blur(3px)",
          }}
        />
      ))}

      {/* Main content */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
        }}
      >
        {/* int. Logo */}
        <div
          style={{
            transform: `scale(${logoScale})`,
            opacity: logoOpacity,
            marginBottom: 40,
          }}
        >
          <div
            style={{
              fontSize: 160,
              fontWeight: 800,
              color: "#ffffff",
              letterSpacing: -4,
              textShadow:
                "0 0 60px rgba(100,136,255,0.8), 0 0 120px rgba(100,136,255,0.4)",
            }}
          >
            int.
          </div>
        </div>

        {/* Tagline */}
        <div
          style={{
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
          }}
        >
          <div
            style={{
              fontSize: 72,
              fontWeight: 700,
              color: "#ffffff",
              letterSpacing: 12,
              textShadow: "0 0 30px rgba(100,136,255,0.5)",
            }}
          >
            構想を、実装する。
          </div>
        </div>

        {/* Subtitle */}
        <div
          style={{
            opacity: subtitleOpacity,
            marginTop: 30,
          }}
        >
          <div
            style={{
              fontSize: 28,
              color: "#8899bb",
              fontWeight: 400,
              letterSpacing: 4,
            }}
          >
            AI-Native Incubation Partner
          </div>
        </div>
      </AbsoluteFill>

      {/* Decorative line */}
      <div
        style={{
          position: "absolute",
          bottom: 120,
          left: "50%",
          transform: "translateX(-50%)",
          width: interpolate(frame, [80, 110], [0, 600], {
            extrapolateRight: "clamp",
            extrapolateLeft: "clamp",
          }),
          height: 2,
          background:
            "linear-gradient(90deg, transparent, #6488ff, transparent)",
        }}
      />
    </AbsoluteFill>
  );
};
