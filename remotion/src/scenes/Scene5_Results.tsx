import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

const results = [
  {
    category: "スポーツ栄養",
    value: 60,
    unit: "%",
    label: "業務時間削減",
    color: "#4ecdc4",
    icon: "⚡",
  },
  {
    category: "観光インバウンド",
    value: 4.2,
    unit: "倍",
    label: "ユーザー継続率",
    color: "#6488ff",
    icon: "📈",
  },
  {
    category: "物流",
    value: 85,
    unit: "%",
    label: "手続き完了率向上",
    color: "#a855f7",
    icon: "🚀",
  },
];

export const Scene5_Results: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title
  const titleOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Fade out
  const fadeOut = interpolate(frame, [130, 150], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, #101828 0%, #0a0a0f 70%)",
        }}
      />

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOpacity,
        }}
      >
        <span
          style={{
            fontSize: 42,
            color: "#ffffff",
            fontWeight: 700,
            letterSpacing: 6,
          }}
        >
          導入実績
        </span>
      </div>

      {/* Result cards */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          paddingTop: 40,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 70,
            justifyContent: "center",
          }}
        >
          {results.map((result, i) => {
            const delay = 15 + i * 25;
            const cardSpring = spring({
              frame: frame - delay,
              fps,
              config: { damping: 10, stiffness: 60 },
            });
            const cardScale = interpolate(cardSpring, [0, 1], [0.5, 1]);
            const cardOpacity = interpolate(cardSpring, [0, 1], [0, 1]);

            // Counter animation
            const counterProgress = interpolate(
              frame,
              [delay + 10, delay + 50],
              [0, 1],
              {
                extrapolateRight: "clamp",
                extrapolateLeft: "clamp",
              }
            );
            const displayValue =
              result.value % 1 === 0
                ? Math.round(result.value * counterProgress)
                : (result.value * counterProgress).toFixed(1);

            // Circle progress
            const circumference = 2 * Math.PI * 80;
            const strokeDashoffset =
              circumference * (1 - counterProgress);

            return (
              <div
                key={i}
                style={{
                  width: 420,
                  padding: "50px 40px",
                  borderRadius: 24,
                  background: "rgba(15,20,35,0.9)",
                  border: `1px solid ${result.color}30`,
                  boxShadow: `0 0 40px rgba(0,0,0,0.5)`,
                  transform: `scale(${cardScale})`,
                  opacity: cardOpacity,
                  textAlign: "center",
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* Background glow */}
                <div
                  style={{
                    position: "absolute",
                    top: -50,
                    left: "50%",
                    transform: "translateX(-50%)",
                    width: 200,
                    height: 200,
                    borderRadius: "50%",
                    background: `radial-gradient(circle, ${result.color}15, transparent 70%)`,
                  }}
                />

                {/* Category */}
                <div
                  style={{
                    fontSize: 20,
                    color: result.color,
                    fontWeight: 600,
                    letterSpacing: 3,
                    marginBottom: 30,
                    textTransform: "uppercase",
                  }}
                >
                  {result.category}
                </div>

                {/* Circular progress + Number */}
                <div
                  style={{
                    position: "relative",
                    width: 200,
                    height: 200,
                    margin: "0 auto 24px",
                  }}
                >
                  <svg
                    width={200}
                    height={200}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      transform: "rotate(-90deg)",
                    }}
                  >
                    {/* Background circle */}
                    <circle
                      cx={100}
                      cy={100}
                      r={80}
                      fill="none"
                      stroke="rgba(255,255,255,0.05)"
                      strokeWidth={6}
                    />
                    {/* Progress circle */}
                    <circle
                      cx={100}
                      cy={100}
                      r={80}
                      fill="none"
                      stroke={result.color}
                      strokeWidth={6}
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                      strokeLinecap="round"
                      style={{
                        filter: `drop-shadow(0 0 8px ${result.color})`,
                      }}
                    />
                  </svg>
                  <div
                    style={{
                      position: "absolute",
                      top: "50%",
                      left: "50%",
                      transform: "translate(-50%, -50%)",
                      textAlign: "center",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 56,
                        fontWeight: 800,
                        color: "#ffffff",
                        textShadow: `0 0 20px ${result.color}80`,
                      }}
                    >
                      {displayValue}
                    </span>
                    <span
                      style={{
                        fontSize: 30,
                        fontWeight: 600,
                        color: result.color,
                      }}
                    >
                      {result.unit}
                    </span>
                  </div>
                </div>

                {/* Label */}
                <div
                  style={{
                    fontSize: 24,
                    color: "#99aabb",
                    fontWeight: 500,
                  }}
                >
                  {result.label}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
