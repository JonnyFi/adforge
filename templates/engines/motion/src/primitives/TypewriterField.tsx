import { interpolate, useCurrentFrame } from "remotion";
import { brand } from "../brand";

export type TypewriterFieldProps = {
  label: string;
  value: string;
  typeStartFrame: number;
  typeDurationFrames?: number;
  labelFontSize?: number;
  valueFontSize?: number;
};

export const TypewriterField: React.FC<TypewriterFieldProps> = ({
  label,
  value,
  typeStartFrame,
  typeDurationFrames = 20,
  labelFontSize = 20,
  valueFontSize = 24,
}) => {
  const frame = useCurrentFrame();
  const typeEnd = typeStartFrame + typeDurationFrames;
  const progress = interpolate(frame, [typeStartFrame, typeEnd], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const visibleChars = Math.floor(value.length * progress);
  const shown = value.slice(0, visibleChars);
  const showCursor = progress > 0 && progress < 1 && frame % 15 < 8;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: labelFontSize, color: brand.muted }}>{label}</div>
      <div
        style={{
          padding: "14px 18px",
          fontSize: valueFontSize,
          color: brand.ink,
          background: "white",
          border: `1.5px solid ${brand.border}`,
          borderRadius: 10,
          minHeight: 28,
        }}
      >
        {shown}
        {showCursor && <span style={{ color: brand.accent }}>|</span>}
      </div>
    </div>
  );
};
