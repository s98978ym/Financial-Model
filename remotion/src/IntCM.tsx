import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { Scene1_Opening } from "./scenes/Scene1_Opening";
import { Scene2_ThreeWalls } from "./scenes/Scene2_ThreeWalls";
import { Scene3_Solution } from "./scenes/Scene3_Solution";
import { Scene4_Phases } from "./scenes/Scene4_Phases";
import { Scene5_Results } from "./scenes/Scene5_Results";
import { Scene6_Ending } from "./scenes/Scene6_Ending";

// 30sec @ 30fps = 900 frames total
// Scene breakdown:
//   Scene 1: 0-5s   (0-150)   Opening - Problem statement
//   Scene 2: 5-10s  (150-300) Three Walls
//   Scene 3: 10-15s (300-450) int. Logo + Solution
//   Scene 4: 15-22s (450-660) Three Phases
//   Scene 5: 22-27s (660-810) Results / Numbers
//   Scene 6: 27-30s (810-900) Ending + CTA

export const IntCM: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0a0a0f",
        fontFamily:
          "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
      }}
    >
      <Sequence from={0} durationInFrames={150}>
        <Scene1_Opening />
      </Sequence>

      <Sequence from={150} durationInFrames={150}>
        <Scene2_ThreeWalls />
      </Sequence>

      <Sequence from={300} durationInFrames={150}>
        <Scene3_Solution />
      </Sequence>

      <Sequence from={450} durationInFrames={210}>
        <Scene4_Phases />
      </Sequence>

      <Sequence from={660} durationInFrames={150}>
        <Scene5_Results />
      </Sequence>

      <Sequence from={810} durationInFrames={90}>
        <Scene6_Ending />
      </Sequence>
    </AbsoluteFill>
  );
};
