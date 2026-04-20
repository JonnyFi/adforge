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
import { ClickRipple, Cursor, Headline, Kicker } from "../primitives";

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
        <Kicker text={variant.kicker} />
        <Headline text={variant.headline} italic={variant.headlineItalic} fontSize={90} />

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

  const showClick = step.showClick !== false;
  const targetCx = offsetX + step.cursorTo.x * scale;
  const targetCy = offsetY + step.cursorTo.y * scale;
  const fromScaled = {
    x: offsetX + step.cursorFrom.x * scale,
    y: offsetY + step.cursorFrom.y * scale,
  };
  const toScaled = { x: targetCx, y: targetCy };

  const captionIn = spring({ frame: frame - 15, fps, config: { damping: 22 } });

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

      {showClick && (
        <ClickRipple at={{ x: targetCx, y: targetCy }} clickFrame={step.clickAt} />
      )}

      <Cursor
        from={fromScaled}
        to={toScaled}
        moveStartFrame={5}
        moveDurationFrames={Math.max(30, step.clickAt - 5)}
        style={step.pointerStyle ?? "cursor"}
      />
    </AbsoluteFill>
  );
};
