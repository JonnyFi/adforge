import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { brand } from "../brand";

export type TickerRowSpec = {
  label: string;
  value: string;
  threshold: number;
};

export type TickerProps = {
  rows: TickerRowSpec[];
  startFrame?: number;
  endFrame?: number;
  background?: string;
  rowPaddingY?: number;
  fontSize?: number;
  labelFontSize?: number;
};

export const Ticker: React.FC<TickerProps> = ({
  rows,
  startFrame = 50,
  endFrame,
  background = "rgba(30,24,19,0.04)",
  rowPaddingY = 22,
  fontSize = 30,
  labelFontSize = 26,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const end = endFrame ?? durationInFrames - 10;
  const progress = interpolate(frame, [startFrame, end], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ background, borderRadius: 28, padding: "12px 36px" }}>
      {rows.map((row, i) => {
        const visible = progress > row.threshold ? 1 : 0;
        return (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: `${rowPaddingY}px 0`,
              borderBottom:
                i === rows.length - 1 ? "none" : "1px solid rgba(30,24,19,0.08)",
              fontSize,
              color: brand.ink,
              opacity: visible,
              transform: `translateX(${(1 - visible) * 20}px)`,
              transition: "all 0.3s",
            }}
          >
            <span
              style={{
                fontFamily: `"${brand.fonts.monoFamily}", monospace`,
                color: brand.muted,
                fontSize: labelFontSize,
              }}
            >
              {row.label}
            </span>
            <span style={{ fontWeight: 500 }}>{row.value}</span>
          </div>
        );
      })}
    </div>
  );
};
