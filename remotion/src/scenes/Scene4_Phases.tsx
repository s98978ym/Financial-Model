import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

const phases = [
  {
    phase: "Phase 1",
    period: "1-2ヶ月",
    title: "戦略策定",
    items: ["テーマ特定", "ROI試算", "PoC計画"],
    color: "#4ecdc4",
    bgGlow: "rgba(78,205,196,0.15)",
  },
  {
    phase: "Phase 2",
    period: "3-6ヶ月",
    title: "実装・自動化",
    items: ["AIエージェント構築", "システム統合"],
    color: "#6488ff",
    bgGlow: "rgba(100,136,255,0.15)",
  },
  {
    phase: "Phase 3",
    period: "2-4ヶ月",
    title: "自走化",
    items: ["ナレッジ移転", "運用体制構築"],
    color: "#a855f7",
    bgGlow: "rgba(168,85,247,0.15)",
  },
];

export const Scene4_Phases: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Section title
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Fade out
  const fadeOut = interpolate(frame, [190, 210], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Progress line
  const lineProgress = interpolate(frame, [30, 180], [0, 100], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, #0f1528 0%, #0a0a0f 70%)",
        }}
      />

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 70,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOpacity,
        }}
      >
        <span
          style={{
            fontSize: 40,
            color: "#6488ff",
            fontWeight: 300,
            letterSpacing: 6,
          }}
        >
          ラボ契約型伴走支援
        </span>
      </div>

      {/* Phase cards */}
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
            gap: 50,
            alignItems: "stretch",
            position: "relative",
          }}
        >
          {phases.map((phase, i) => {
            const delay = 30 + i * 45;
            const phaseSpring = spring({
              frame: frame - delay,
              fps,
              config: { damping: 12, stiffness: 70 },
            });
            const slideX = interpolate(phaseSpring, [0, 1], [100, 0]);
            const cardOpacity = interpolate(phaseSpring, [0, 1], [0, 1]);

            // Active glow when phase is "current"
            const isActive =
              frame > delay + 15 &&
              (i < 2 ? frame < delay + 45 + 30 : true);
            const glowIntensity = isActive ? 1 : 0.3;

            return (
              <div
                key={i}
                style={{
                  width: 440,
                  padding: "40px 36px",
                  borderRadius: 20,
                  background: `linear-gradient(145deg, rgba(15,20,40,0.95), rgba(10,10,20,0.95))`,
                  border: `1px solid ${phase.color}50`,
                  boxShadow: `0 0 ${30 * glowIntensity}px ${phase.bgGlow}`,
                  transform: `translateX(${slideX}px)`,
                  opacity: cardOpacity,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* Top accent */}
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 4,
                    background: `linear-gradient(90deg, ${phase.color}, transparent)`,
                  }}
                />

                {/* Phase badge */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 20,
                  }}
                >
                  <span
                    style={{
                      fontSize: 22,
                      color: phase.color,
                      fontWeight: 700,
                      letterSpacing: 3,
                    }}
                  >
                    {phase.phase}
                  </span>
                  <span
                    style={{
                      fontSize: 18,
                      color: "#667788",
                      fontWeight: 400,
                      background: "rgba(255,255,255,0.05)",
                      padding: "4px 14px",
                      borderRadius: 20,
                    }}
                  >
                    {phase.period}
                  </span>
                </div>

                {/* Title */}
                <div
                  style={{
                    fontSize: 36,
                    color: "#ffffff",
                    fontWeight: 700,
                    marginBottom: 24,
                  }}
                >
                  {phase.title}
                </div>

                {/* Items */}
                {phase.items.map((item, j) => {
                  const itemDelay = delay + 15 + j * 8;
                  const itemOpacity = interpolate(
                    frame,
                    [itemDelay, itemDelay + 10],
                    [0, 1],
                    {
                      extrapolateRight: "clamp",
                      extrapolateLeft: "clamp",
                    }
                  );
                  return (
                    <div
                      key={j}
                      style={{
                        fontSize: 22,
                        color: "#99aabb",
                        marginBottom: 10,
                        opacity: itemOpacity,
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                      }}
                    >
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: phase.color,
                          opacity: 0.7,
                          flexShrink: 0,
                        }}
                      />
                      {item}
                    </div>
                  );
                })}
              </div>
            );
          })}

          {/* Connection arrows between phases */}
          {[0, 1].map((i) => {
            const arrowDelay = 75 + i * 45;
            const arrowOpacity = interpolate(
              frame,
              [arrowDelay, arrowDelay + 15],
              [0, 1],
              {
                extrapolateRight: "clamp",
                extrapolateLeft: "clamp",
              }
            );
            return (
              <div
                key={`arrow-${i}`}
                style={{
                  position: "absolute",
                  top: "50%",
                  left: `${33 * (i + 1)}%`,
                  transform: "translate(-50%, -50%)",
                  fontSize: 36,
                  color: "#6488ff",
                  opacity: arrowOpacity,
                  zIndex: 10,
                  textShadow: "0 0 15px rgba(100,136,255,0.8)",
                }}
              >
                →
              </div>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* Bottom progress bar */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: 200,
          right: 200,
          height: 4,
          background: "rgba(255,255,255,0.1)",
          borderRadius: 2,
        }}
      >
        <div
          style={{
            width: `${lineProgress}%`,
            height: "100%",
            background: "linear-gradient(90deg, #4ecdc4, #6488ff, #a855f7)",
            borderRadius: 2,
            boxShadow:
              "0 0 15px rgba(100,136,255,0.5), 0 0 30px rgba(100,136,255,0.3)",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
