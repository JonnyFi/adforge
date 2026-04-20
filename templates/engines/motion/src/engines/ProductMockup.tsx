import {
  AbsoluteFill,
  interpolate,
  spring,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand } from "../brand";

export type MockupVariant = {
  kicker: string;
  headline: string;
  headlineItalic: string;
  appName: string;
  navItems: string[];
  activeNav: number;
  targetButton: { x: number; y: number; label: string };
  formFields: { label: string; value: string }[];
  successMessage: string;
};

export const ProductMockup: React.FC<{ variant: MockupVariant }> = ({ variant }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headlineIn = spring({ frame, fps, config: { damping: 20 } });
  const appIn = spring({ frame: frame - 20, fps, config: { damping: 24 } });

  const cursorStart = { x: 960, y: 300 };
  const cursorTarget = variant.targetButton;
  const moveProgress = spring({
    frame: frame - 30,
    fps,
    config: { damping: 30, stiffness: 80 },
    durationInFrames: 50,
  });
  const cursorX = interpolate(moveProgress, [0, 1], [cursorStart.x, cursorTarget.x]);
  const cursorY = interpolate(moveProgress, [0, 1], [cursorStart.y, cursorTarget.y]);

  const clickFrame = 80;
  const clickRipple = interpolate(frame, [clickFrame, clickFrame + 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: brand.cream, fontFamily: "Inter, sans-serif" }}>
      <div
        style={{
          padding: "72px 72px 48px",
          display: "flex",
          flexDirection: "column",
          gap: 36,
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
            fontSize: 100,
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
            flex: 1,
            background: brand.card,
            borderRadius: 32,
            border: `1.5px solid ${brand.border}`,
            boxShadow: "0 40px 80px rgba(30, 24, 19, 0.12)",
            position: "relative",
            overflow: "hidden",
            transform: `translateY(${(1 - appIn) * 40}px)`,
            opacity: appIn,
          }}
        >
          <div
            style={{
              height: 70,
              display: "flex",
              alignItems: "center",
              padding: "0 32px",
              gap: 16,
              borderBottom: `1px solid ${brand.border}`,
            }}
          >
            <div style={{ display: "flex", gap: 8 }}>
              <Dot color="#ff5f57" />
              <Dot color="#febc2e" />
              <Dot color="#28c840" />
            </div>
            <div
              style={{
                flex: 1,
                textAlign: "center",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 20,
                color: brand.muted,
              }}
            >
              {variant.appName}
            </div>
          </div>

          <div style={{ display: "flex", height: "calc(100% - 70px)" }}>
            <div
              style={{
                width: 280,
                padding: "32px 20px",
                borderRight: `1px solid ${brand.border}`,
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              {variant.navItems.map((item, i) => (
                <div
                  key={i}
                  style={{
                    padding: "16px 20px",
                    borderRadius: 12,
                    fontSize: 26,
                    color: i === variant.activeNav ? brand.accent : brand.ink,
                    background: i === variant.activeNav ? "rgba(184,121,26,0.08)" : "transparent",
                    fontWeight: i === variant.activeNav ? 600 : 400,
                  }}
                >
                  {item}
                </div>
              ))}
            </div>

            <div
              style={{
                flex: 1,
                padding: "40px 44px",
                display: "flex",
                flexDirection: "column",
                gap: 28,
                position: "relative",
              }}
            >
              <Sequence from={0} durationInFrames={100}>
                <EmptyState
                  targetButton={variant.targetButton}
                  clickRipple={clickRipple}
                />
              </Sequence>

              <Sequence from={100} durationInFrames={100}>
                <FormStep fields={variant.formFields} frame={frame - 100} fps={fps} />
              </Sequence>

              <Sequence from={200}>
                <SuccessStep
                  message={variant.successMessage}
                  frame={frame - 200}
                  fps={fps}
                />
              </Sequence>
            </div>
          </div>

          <div
            style={{
              position: "absolute",
              left: cursorX,
              top: cursorY,
              width: 28,
              height: 28,
              pointerEvents: "none",
              opacity: frame > 250 ? 0 : 1,
            }}
          >
            <svg width="28" height="28" viewBox="0 0 28 28">
              <path
                d="M4 2 L4 22 L10 17 L13 24 L16 23 L13 16 L20 16 Z"
                fill={brand.ink}
                stroke="white"
                strokeWidth="1.5"
              />
            </svg>
          </div>

          {clickRipple > 0 && clickRipple < 1 && (
            <div
              style={{
                position: "absolute",
                left: cursorTarget.x - 40,
                top: cursorTarget.y - 40,
                width: 80,
                height: 80,
                borderRadius: "50%",
                border: `3px solid ${brand.accent}`,
                opacity: 1 - clickRipple,
                transform: `scale(${0.5 + clickRipple * 1.5})`,
                pointerEvents: "none",
              }}
            />
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Dot: React.FC<{ color: string }> = ({ color }) => (
  <div style={{ width: 14, height: 14, borderRadius: "50%", background: color }} />
);

const EmptyState: React.FC<{
  targetButton: { x: number; y: number; label: string };
  clickRipple: number;
}> = ({ targetButton, clickRipple }) => {
  const frame = useCurrentFrame();
  const fadeOut = interpolate(frame, [80, 98], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div style={{ opacity: fadeOut, display: "flex", flexDirection: "column", gap: 24 }}>
      <button
        style={{
          position: "absolute",
          left: targetButton.x - 352 - 100,
          top: targetButton.y - 70 - 40,
          padding: "20px 40px",
          fontSize: 26,
          fontWeight: 600,
          color: "white",
          background: clickRipple > 0 ? "rgba(184,121,26,0.8)" : brand.accent,
          borderRadius: 14,
          border: "none",
          boxShadow: clickRipple > 0 ? "none" : "0 8px 24px rgba(184,121,26,0.3)",
          transform: clickRipple > 0 ? "scale(0.97)" : "scale(1)",
        }}
      >
        {targetButton.label}
      </button>
    </div>
  );
};

const FormStep: React.FC<{
  fields: { label: string; value: string }[];
  frame: number;
  fps: number;
}> = ({ fields, frame, fps }) => {
  const slideIn = spring({ frame, fps, config: { damping: 22 } });
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 24,
        opacity: slideIn,
        transform: `translateY(${(1 - slideIn) * 30}px)`,
      }}
    >
      {fields.map((field, i) => {
        const typeStart = 15 + i * 25;
        const typeEnd = typeStart + 20;
        const typeProgress = interpolate(frame, [typeStart, typeEnd], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const visibleChars = Math.floor(field.value.length * typeProgress);
        const shownValue = field.value.slice(0, visibleChars);
        const showCursor = typeProgress > 0 && typeProgress < 1 && frame % 15 < 8;
        return (
          <div key={i} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ fontSize: 20, color: brand.muted }}>{field.label}</div>
            <div
              style={{
                padding: "14px 18px",
                fontSize: 24,
                color: brand.ink,
                background: "white",
                border: `1.5px solid ${brand.border}`,
                borderRadius: 10,
                minHeight: 28,
              }}
            >
              {shownValue}
              {showCursor && <span style={{ color: brand.accent }}>|</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const SuccessStep: React.FC<{ message: string; frame: number; fps: number }> = ({
  message,
  frame,
  fps,
}) => {
  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 120 } });
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        gap: 24,
        transform: `scale(${pop})`,
        opacity: pop,
      }}
    >
      <div
        style={{
          width: 140,
          height: 140,
          borderRadius: "50%",
          background: brand.success,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 80,
          color: "white",
        }}
      >
        ✓
      </div>
      <div
        style={{
          fontSize: 34,
          color: brand.ink,
          fontWeight: 600,
          textAlign: "center",
          maxWidth: 500,
          lineHeight: 1.25,
          whiteSpace: "pre-line",
        }}
      >
        {message}
      </div>
    </div>
  );
};
