import {
  AbsoluteFill,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand } from "../brand";
import {
  ClickRipple,
  Cursor,
  Headline,
  Kicker,
  TypewriterField,
} from "../primitives";

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
  const appIn = spring({ frame: frame - 20, fps, config: { damping: 24 } });
  const clickFrame = 80;

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
        <Kicker text={variant.kicker} />
        <Headline text={variant.headline} italic={variant.headlineItalic} fontSize={100} />

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
          <BrowserChrome appName={variant.appName} />

          <div style={{ display: "flex", height: "calc(100% - 70px)" }}>
            <Sidebar items={variant.navItems} active={variant.activeNav} />
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
                <EmptyState targetButton={variant.targetButton} clickFrame={clickFrame} />
              </Sequence>
              <Sequence from={100} durationInFrames={100}>
                <FormStep fields={variant.formFields} />
              </Sequence>
              <Sequence from={200}>
                <SuccessStep message={variant.successMessage} />
              </Sequence>
            </div>
          </div>

          <Cursor
            from={{ x: 960, y: 300 }}
            to={variant.targetButton}
            moveStartFrame={30}
            moveDurationFrames={50}
            style="cursor"
          />
          <ClickRipple at={variant.targetButton} clickFrame={clickFrame} durationFrames={25} size={80} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const BrowserChrome: React.FC<{ appName: string }> = ({ appName }) => (
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
      {appName}
    </div>
  </div>
);

const Dot: React.FC<{ color: string }> = ({ color }) => (
  <div style={{ width: 14, height: 14, borderRadius: "50%", background: color }} />
);

const Sidebar: React.FC<{ items: string[]; active: number }> = ({ items, active }) => (
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
    {items.map((item, i) => (
      <div
        key={i}
        style={{
          padding: "16px 20px",
          borderRadius: 12,
          fontSize: 26,
          color: i === active ? brand.accent : brand.ink,
          background: i === active ? "rgba(184,121,26,0.08)" : "transparent",
          fontWeight: i === active ? 600 : 400,
        }}
      >
        {item}
      </div>
    ))}
  </div>
);

const EmptyState: React.FC<{
  targetButton: { x: number; y: number; label: string };
  clickFrame: number;
}> = ({ targetButton, clickFrame }) => {
  const frame = useCurrentFrame();
  const fadeOut = interpolate(frame, [80, 98], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pressed = frame >= clickFrame && frame <= clickFrame + 8;
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
          background: pressed ? "rgba(184,121,26,0.8)" : brand.accent,
          borderRadius: 14,
          border: "none",
          boxShadow: pressed ? "none" : "0 8px 24px rgba(184,121,26,0.3)",
          transform: pressed ? "scale(0.97)" : "scale(1)",
        }}
      >
        {targetButton.label}
      </button>
    </div>
  );
};

const FormStep: React.FC<{ fields: { label: string; value: string }[] }> = ({ fields }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
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
      {fields.map((field, i) => (
        <TypewriterField
          key={i}
          label={field.label}
          value={field.value}
          typeStartFrame={15 + i * 25}
        />
      ))}
    </div>
  );
};

const SuccessStep: React.FC<{ message: string }> = ({ message }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
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
