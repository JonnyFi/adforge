import { interpolate, useCurrentFrame } from "remotion";
import { brand } from "../brand";

export type KickerProps = {
  text: string;
  fontSize?: number;
  color?: string;
  trackingPx?: number;
  fadeInEnd?: number;
};

export const Kicker: React.FC<KickerProps> = ({
  text,
  fontSize = 26,
  color = brand.muted,
  trackingPx = 3,
  fadeInEnd = 15,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, fadeInEnd], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div
      style={{
        fontFamily: `"${brand.fonts.monoFamily}", monospace`,
        fontSize,
        letterSpacing: trackingPx,
        color,
        textTransform: "uppercase",
        opacity,
      }}
    >
      {text}
    </div>
  );
};
