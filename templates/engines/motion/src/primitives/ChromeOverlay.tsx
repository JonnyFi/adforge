import brandJson from "../../../../brand.json";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

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
  padding?: number;
  fadeInAt?: number;
  // image mode — if path is set, renders image instead of text
  path?: string;
  height?: number;
  // text mode (used when path is not set)
  style?: "serif-italic" | "sans-medium" | "mono-uppercase";
  fontSize?: number;
  color?: "accent" | "ink" | "muted" | string;
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
 * Renders brand-level chrome (wordmark or logo) on top of a composition.
 * Reads brand.json → `chrome`. Renders nothing if chrome isn't configured.
 *
 * This is opt-in consistency: brands that want a mark on every creative
 * set it here once; compositions stay chrome-free so every brief can produce
 * a structurally different ad.
 *
 * If `chrome.wordmark.path` is set, renders the image (must live under
 * `engines/motion/public/` for Remotion's staticFile to resolve it).
 * Otherwise renders brand.wordmark / brand.name as text.
 */
export const ChromeOverlay: React.FC = () => {
  const wm = chrome.wordmark;
  if (!wm || wm.show === false) return null;
  if (wm.path) {
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <LogoImage config={wm} />
      </AbsoluteFill>
    );
  }
  const text =
    (brandJson as { wordmark?: string; name?: string }).wordmark ??
    (brandJson as { wordmark?: string; name?: string }).name ??
    "";
  if (!text) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <WordmarkText text={text} config={wm} />
    </AbsoluteFill>
  );
};

const positionStyle = (position: Position, padding: number): React.CSSProperties => {
  const s: React.CSSProperties = { position: "absolute" };
  if (position.startsWith("bottom")) s.bottom = padding;
  if (position.startsWith("top")) s.top = padding;
  if (position.endsWith("left")) s.left = padding;
  if (position.endsWith("right")) s.right = padding;
  if (position.endsWith("center")) {
    s.left = "50%";
    s.transform = "translateX(-50%)";
  }
  return s;
};

const useFadeIn = (fadeInAt: number) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [fadeInAt, fadeInAt + 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};

const LogoImage: React.FC<{ config: WordmarkConfig }> = ({ config }) => {
  const position: Position = config.position ?? "bottom-left";
  const padding = config.padding ?? 72;
  const height = config.height ?? 120;
  const opacity = useFadeIn(config.fadeInAt ?? 0);
  return (
    <Img
      src={staticFile(config.path!)}
      style={{ ...positionStyle(position, padding), height, width: "auto", opacity }}
    />
  );
};

const WordmarkText: React.FC<{ text: string; config: WordmarkConfig }> = ({ text, config }) => {
  const position: Position = config.position ?? "bottom-left";
  const padding = config.padding ?? 72;
  const opacity = useFadeIn(config.fadeInAt ?? 0);
  const style = config.style ?? "serif-italic";

  const baseStyle: React.CSSProperties = {
    ...positionStyle(position, padding),
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

  return <div style={baseStyle}>{text}</div>;
};
