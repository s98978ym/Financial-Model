import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

const walls = [
  {
    icon: "?",
    title: "活用テーマの不明確さ",
    desc: "どこにAIを使えばROIが出るか不透明",
    color: "#ff6b6b",
    glowColor: "rgba(255,107,107,0.3)",
  },
  {
    icon: "△",
    title: "社内体制の制約",
    desc: "AI専門チームの不在、既存業務との兼ね合い",
    color: "#ffd93d",
    glowColor: "rgba(255,217,61,0.3)",
  },
  {
    icon: "!",
    title: "専門人材の不在",
    desc: "プロンプト設計やモデル選定ができる人材の欠如",
    color: "#ff8a5c",
    glowColor: "rgba(255,138,92,0.3)",
  },
];

export const Scene2_ThreeWalls: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title animation
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const titleY = interpolate(frame, [0, 20], [-30, 0], {
    extrapolateRight: "clamp",
  });

  // Fade out
  const fadeOut = interpolate(frame, [130, 150], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Background pulse
  const pulseOpacity = interpolate(
    Math.sin(frame * 0.05),
    [-1, 1],
    [0.02, 0.08]
  );

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, #1a1020 0%, #0a0a0f 70%)",
        }}
      />

      {/* Danger pulse rings */}
      {[0, 1, 2].map((i) => {
        const ringFrame = (frame - i * 20) % 90;
        const ringScale = interpolate(ringFrame, [0, 90], [0.5, 2.5]);
        const ringOpacity = interpolate(ringFrame, [0, 90], [0.3, 0]);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              width: 400,
              height: 400,
              borderRadius: "50%",
              border: "1px solid rgba(255,100,100,0.3)",
              transform: `translate(-50%, -50%) scale(${ringScale})`,
              opacity: ringOpacity,
            }}
          />
        );
      })}

      {/* Section title */}
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        <span
          style={{
            fontSize: 36,
            color: "#ff6b6b",
            fontWeight: 600,
            letterSpacing: 8,
            textTransform: "uppercase",
          }}
        >
          AI導入の
        </span>
        <span
          style={{
            fontSize: 52,
            color: "#ffffff",
            fontWeight: 700,
            letterSpacing: 8,
            marginLeft: 10,
          }}
        >
          3つの壁
        </span>
      </div>

      {/* Three wall cards */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          paddingTop: 60,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 60,
            justifyContent: "center",
            alignItems: "stretch",
          }}
        >
          {walls.map((wall, i) => {
            const delay = 25 + i * 25;
            const cardSpring = spring({
              frame: frame - delay,
              fps,
              config: { damping: 12, stiffness: 80 },
            });
            const cardScale = interpolate(cardSpring, [0, 1], [0.3, 1]);
            const cardOpacity = interpolate(cardSpring, [0, 1], [0, 1]);

            // Shake effect on appear
            const shakeX =
              frame > delay && frame < delay + 10
                ? Math.sin(frame * 2) * (10 - (frame - delay))
                : 0;

            return (
              <div
                key={i}
                style={{
                  width: 420,
                  padding: "50px 40px",
                  borderRadius: 24,
                  background: "rgba(20,20,30,0.9)",
                  border: `1px solid ${wall.color}40`,
                  boxShadow: `0 0 40px ${wall.glowColor}, inset 0 0 30px rgba(0,0,0,0.5)`,
                  transform: `scale(${cardScale}) translateX(${shakeX}px)`,
                  opacity: cardOpacity,
                  textAlign: "center",
                  backdropFilter: "blur(10px)",
                }}
              >
                {/* Icon */}
                <div
                  style={{
                    fontSize: 64,
                    color: wall.color,
                    marginBottom: 24,
                    fontWeight: 800,
                    textShadow: `0 0 20px ${wall.glowColor}`,
                  }}
                >
                  {wall.icon}
                </div>

                {/* Title */}
                <div
                  style={{
                    fontSize: 30,
                    color: "#ffffff",
                    fontWeight: 700,
                    marginBottom: 16,
                    lineHeight: 1.4,
                  }}
                >
                  {wall.title}
                </div>

                {/* Description */}
                <div
                  style={{
                    fontSize: 20,
                    color: "#888899",
                    lineHeight: 1.6,
                    fontWeight: 400,
                  }}
                >
                  {wall.desc}
                </div>

                {/* Bottom accent line */}
                <div
                  style={{
                    marginTop: 30,
                    height: 3,
                    background: `linear-gradient(90deg, transparent, ${wall.color}, transparent)`,
                    borderRadius: 2,
                    opacity: 0.6,
                  }}
                />
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
