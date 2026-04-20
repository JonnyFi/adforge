import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { brand } from "../brand";

export type CursorProps = {
  from: { x: number; y: number };
  to: { x: number; y: number };
  moveStartFrame?: number;
  moveDurationFrames?: number;
  style?: "cursor" | "tap";
};

export const Cursor: React.FC<CursorProps> = ({
  from,
  to,
  moveStartFrame = 0,
  moveDurationFrames = 50,
  style = "cursor",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = spring({
    frame: frame - moveStartFrame,
    fps,
    config: { damping: 30, stiffness: 80 },
    durationInFrames: moveDurationFrames,
  });
  const x = interpolate(t, [0, 1], [from.x, to.x]);
  const y = interpolate(t, [0, 1], [from.y, to.y]);

  if (style === "tap") {
    return (
      <div
        style={{
          position: "absolute",
          left: x - 35,
          top: y - 35,
          width: 70,
          height: 70,
          borderRadius: "50%",
          background: "rgba(30,24,19,0.28)",
          border: "3px solid rgba(255,255,255,0.85)",
          pointerEvents: "none",
          boxShadow: "0 6px 18px rgba(0,0,0,0.25)",
        }}
      />
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: 40,
        height: 40,
        pointerEvents: "none",
        filter: "drop-shadow(0 4px 10px rgba(0,0,0,0.3))",
      }}
    >
      <svg width="40" height="40" viewBox="0 0 28 28">
        <path
          d="M4 2 L4 22 L10 17 L13 24 L16 23 L13 16 L20 16 Z"
          fill={brand.ink}
          stroke="white"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  );
};

export type ClickRippleProps = {
  at: { x: number; y: number };
  clickFrame: number;
  durationFrames?: number;
  size?: number;
  color?: string;
};

export const ClickRipple: React.FC<ClickRippleProps> = ({
  at,
  clickFrame,
  durationFrames = 22,
  size = 110,
  color = brand.accent,
}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [clickFrame, clickFrame + durationFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (t <= 0 || t >= 1) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: at.x - size / 2,
        top: at.y - size / 2,
        width: size,
        height: size,
        borderRadius: "50%",
        border: `4px solid ${color}`,
        opacity: 1 - t,
        transform: `scale(${0.4 + t * 1.8})`,
        pointerEvents: "none",
      }}
    />
  );
};
