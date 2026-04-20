import brandJson from "../../../../brand.json";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

type Position =
  | "bottom-left"
  | "bottom-right"
  | "bottom-center"
  | "top-left"
  | "top-right"
  | "top-center";

type WordmarkConfig = {
  show?: boolean;
  position?: Position;
  style?: "serif-italic" | "sans-medium" | "mono-uppercase";
  fontSize?: number;
  color?: "accent" | "ink" | "muted" | string;
  padding?: number;
  fadeInAt?: number;
};

type ChromeConfig = {
  wordmark?: WordmarkConfig;
};

const chrome: ChromeConfig = (brandJson as { chrome?: ChromeConfig }).chrome ?? {};

const resolveColor = (key?: string): string => {
  const c = (brandJson.colors as Record<string, string>) ?? {};
  if (!key) return c.accent;
  if (key in c) return c[key];
  return key;
};

/**
 * Renders brand-level chrome (wordmark, etc.) on top of a composition.
 * Reads brand.json → `chrome`. Renders nothing if chrome isn't configured.
 *
 * This is opt-in consistency: brands that want a wordmark on every creative
 * set it here once; compositions stay chrome-free so every brief can produce
 * a structurally different ad.
 */
export const ChromeOverlay: React.FC = () => {
  const wm = chrome.wordmark;
  if (!wm || wm.show === false) return null;
  const text =
    (brandJson as { wordmark?: string; name?: string }).wordmark ??
    (brandJson as { wordmark?: string; name?: string }).name ??
    "";
  if (!text) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <Wordmark text={text} config={wm} />
    </AbsoluteFill>
  );
};

const Wordmark: React.FC<{ text: string; config: WordmarkConfig }> = ({ text, config }) => {
  const frame = useCurrentFrame();
  const position: Position = config.position ?? "bottom-left";
  const padding = config.padding ?? 72;
  const fadeInAt = config.fadeInAt ?? 0;
  const opacity = interpolate(frame, [fadeInAt, fadeInAt + 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const style = config.style ?? "serif-italic";
  const baseStyle: React.CSSProperties = {
    position: "absolute",
    color: resolveColor(config.color ?? "accent"),
    opacity,
  };

  if (style === "serif-italic") {
    baseStyle.fontFamily = "Instrument Serif, serif";
    baseStyle.fontStyle = "italic";
    baseStyle.fontSize = config.fontSize ?? 48;
  } else if (style === "sans-medium") {
    baseStyle.fontFamily = "Inter, sans-serif";
    baseStyle.fontWeight = 500;
    baseStyle.fontSize = config.fontSize ?? 40;
  } else if (style === "mono-uppercase") {
    baseStyle.fontFamily = "JetBrains Mono, monospace";
    baseStyle.textTransform = "uppercase";
    baseStyle.letterSpacing = 3;
    baseStyle.fontSize = config.fontSize ?? 30;
  }

  if (position.startsWith("bottom")) baseStyle.bottom = padding;
  if (position.startsWith("top")) baseStyle.top = padding;
  if (position.endsWith("left")) baseStyle.left = padding;
  if (position.endsWith("right")) baseStyle.right = padding;
  if (position.endsWith("center")) {
    baseStyle.left = "50%";
    baseStyle.transform = "translateX(-50%)";
  }

  return <div style={baseStyle}>{text}</div>;
};
