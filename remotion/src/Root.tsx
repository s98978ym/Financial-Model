import { Composition } from "remotion";
import { IntCM } from "./IntCM";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="IntCM"
        component={IntCM}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
