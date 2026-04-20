import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { brand } from "../brand";

export type HeadlineProps = {
  text: string;
  italic?: string;
  fontSize?: number;
  color?: string;
  italicColor?: string;
  delayFrames?: number;
  translateY?: number;
};

export const Headline: React.FC<HeadlineProps> = ({
  text,
  italic,
  fontSize = 110,
  color = brand.ink,
  italicColor = brand.accent,
  delayFrames = 0,
  translateY = 40,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = spring({ frame: frame - delayFrames, fps, config: { damping: 20 } });
  return (
    <div
      style={{
        fontFamily: `"${brand.fonts.serifFamily}", serif`,
        fontSize,
        color,
        lineHeight: 1.02,
        transform: `translateY(${(1 - t) * translateY}px)`,
        opacity: t,
      }}
    >
      {text}
      {italic && (
        <>
          <br />
          <span style={{ fontStyle: "italic", color: italicColor }}>{italic}</span>
        </>
      )}
    </div>
  );
};
