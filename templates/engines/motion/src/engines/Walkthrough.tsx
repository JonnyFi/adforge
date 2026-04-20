import {
  AbsoluteFill,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand } from "../brand";

export type ScreenStep = {
  image: string;
  imageWidth: number;
  imageHeight: number;
  cursorFrom: { x: number; y: number };
  cursorTo: { x: number; y: number };
  clickAt: number;
  caption: string;
  showClick?: boolean;
  pointerStyle?: "cursor" | "tap";
};

export type WalkthroughVariant = {
  kicker: string;
  headline: string;
  headlineItalic: string;
  steps: ScreenStep[];
};

const STEP_FRAMES = 90;
const STAGE_W = 960;
const STAGE_H = 1370;

export const Walkthrough: React.FC<{ variant: WalkthroughVariant }> = ({ variant }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const headlineIn = spring({ frame, fps, config: { damping: 20 } });

  return (
    <AbsoluteFill style={{ backgroundColor: brand.cream, fontFamily: "Inter, sans-serif" }}>
      <div
        style={{
          padding: "60px 60px 48px",
          display: "flex",
          flexDirection: "column",
          gap: 28,
          height: "100%",
        }}
      >
        <div
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 26,
            letterSpacing: 3,
            color: brand.muted,
            opacity: interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" }),
          }}
        >
          {variant.kicker}
        </div>

        <div
          style={{
            fontFamily: "Instrument Serif, serif",
            fontSize: 90,
            color: brand.ink,
            lineHeight: 1.02,
            transform: `translateY(${(1 - headlineIn) * 40}px)`,
            opacity: headlineIn,
          }}
        >
          {variant.headline}
          <br />
          <span style={{ fontStyle: "italic", color: brand.accent }}>
            {variant.headlineItalic}
          </span>
        </div>

        <div
          style={{
            width: STAGE_W,
            height: STAGE_H,
            position: "relative",
            alignSelf: "center",
          }}
        >
          {variant.steps.map((step, i) => (
            <Sequence key={i} from={i * STEP_FRAMES} durationInFrames={STEP_FRAMES}>
              <Step step={step} stepIndex={i} />
            </Sequence>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Step: React.FC<{ step: ScreenStep; stepIndex: number }> = ({ step, stepIndex }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, [STEP_FRAMES - 12, STEP_FRAMES], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = Math.min(fadeIn, fadeOut);

  const imgRatio = step.imageWidth / step.imageHeight;
  const stageRatio = STAGE_W / STAGE_H;
  let frameW: number;
  let frameH: number;
  if (imgRatio > stageRatio) {
    frameW = STAGE_W;
    frameH = STAGE_W / imgRatio;
  } else {
    frameH = STAGE_H;
    frameW = STAGE_H * imgRatio;
  }
  const offsetX = (STAGE_W - frameW) / 2;
  const offsetY = (STAGE_H - frameH) / 2;
  const scale = frameW / step.imageWidth;

  const moveProgress = spring({
    frame: frame - 5,
    fps,
    config: { damping: 30, stiffness: 70 },
    durationInFrames: Math.max(30, step.clickAt - 5),
  });
  const nativeCx = interpolate(moveProgress, [0, 1], [step.cursorFrom.x, step.cursorTo.x]);
  const nativeCy = interpolate(moveProgress, [0, 1], [step.cursorFrom.y, step.cursorTo.y]);
  const cx = offsetX + nativeCx * scale;
  const cy = offsetY + nativeCy * scale;

  const showClick = step.showClick !== false;
  const clickRipple = showClick
    ? interpolate(frame, [step.clickAt, step.clickAt + 22], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;
  const targetCx = offsetX + step.cursorTo.x * scale;
  const targetCy = offsetY + step.cursorTo.y * scale;

  const captionIn = spring({ frame: frame - 15, fps, config: { damping: 22 } });
  const isTap = step.pointerStyle === "tap";

  return (
    <AbsoluteFill style={{ opacity }}>
      <div
        style={{
          position: "absolute",
          left: offsetX,
          top: offsetY,
          width: frameW,
          height: frameH,
          borderRadius: 48,
          overflow: "hidden",
          boxShadow: "0 40px 100px rgba(30, 24, 19, 0.18)",
        }}
      >
        <Img
          src={staticFile(step.image)}
          style={{ width: "100%", height: "100%", display: "block" }}
        />
      </div>

      <div
        style={{
          position: "absolute",
          top: 28,
          left: 28,
          padding: "14px 24px",
          background: "rgba(30, 24, 19, 0.88)",
          color: "white",
          fontSize: 24,
          fontWeight: 500,
          borderRadius: 28,
          letterSpacing: 0.3,
          transform: `translateY(${(1 - captionIn) * 20}px)`,
          opacity: captionIn,
          backdropFilter: "blur(8px)",
        }}
      >
        {stepIndex + 1}. {step.caption}
      </div>

      {showClick && clickRipple > 0 && clickRipple < 1 && (
        <div
          style={{
            position: "absolute",
            left: targetCx - 55,
            top: targetCy - 55,
            width: 110,
            height: 110,
            borderRadius: "50%",
            border: `4px solid ${brand.accent}`,
            opacity: 1 - clickRipple,
            transform: `scale(${0.4 + clickRipple * 1.8})`,
            pointerEvents: "none",
          }}
        />
      )}

      {isTap ? (
        <div
          style={{
            position: "absolute",
            left: cx - 35,
            top: cy - 35,
            width: 70,
            height: 70,
            borderRadius: "50%",
            background: "rgba(30,24,19,0.28)",
            border: "3px solid rgba(255,255,255,0.85)",
            pointerEvents: "none",
            boxShadow: "0 6px 18px rgba(0,0,0,0.25)",
          }}
        />
      ) : (
        <div
          style={{
            position: "absolute",
            left: cx,
            top: cy,
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
      )}
    </AbsoluteFill>
  );
};
