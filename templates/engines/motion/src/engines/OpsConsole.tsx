import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand } from "../brand";

export type TranscriptLine = { at: number; text: string };
export type TickerRowType = { label: string; value: string; threshold: number };

export type OpsConsoleVariant = {
  kicker: string;
  headline: string;
  headlineItalic: string;
  call: {
    status: string;
    caller: string;
    subline: string;
    avatarLabel: string;
  };
  transcript: TranscriptLine[];
  ticker: TickerRowType[];
};

export const OpsConsole: React.FC<{ variant: OpsConsoleVariant }> = ({ variant }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const headlineIn = spring({ frame, fps, config: { damping: 20 } });
  const callIn = spring({ frame: frame - 25, fps, config: { damping: 22 } });
  const tickerProgress = interpolate(frame, [50, durationInFrames - 10], [0, 1], {
    extrapolateRight: "clamp",
  });

  const callSeconds = Math.max(0, Math.floor((frame - 25) / fps));
  const mm = String(Math.floor(callSeconds / 60)).padStart(2, "0");
  const ss = String(callSeconds % 60).padStart(2, "0");

  return (
    <AbsoluteFill style={{ backgroundColor: brand.cream, fontFamily: "Inter, sans-serif" }}>
      <div
        style={{
          padding: "72px 72px 64px",
          display: "flex",
          flexDirection: "column",
          gap: 40,
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
            fontSize: 110,
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

        <CallCard
          mm={mm}
          ss={ss}
          frame={frame}
          fps={fps}
          visible={callIn}
          call={variant.call}
          transcript={variant.transcript}
        />

        <div style={{ flex: 1 }} />

        <div
          style={{
            background: "rgba(30,24,19,0.04)",
            borderRadius: 28,
            padding: "12px 36px",
          }}
        >
          {variant.ticker.map((row, i) => (
            <TickerRow
              key={i}
              label={row.label}
              value={row.value}
              progress={tickerProgress}
              threshold={row.threshold}
              last={i === variant.ticker.length - 1}
            />
          ))}
        </div>

        {brand.wordmark && (
          <div
            style={{
              fontFamily: "Instrument Serif, serif",
              fontSize: 48,
              fontStyle: "italic",
              color: brand.accent,
            }}
          >
            {brand.wordmark}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

const CallCard: React.FC<{
  mm: string;
  ss: string;
  frame: number;
  fps: number;
  visible: number;
  call: OpsConsoleVariant["call"];
  transcript: TranscriptLine[];
}> = ({ mm, ss, frame, fps, visible, call, transcript }) => (
  <div
    style={{
      background: brand.card,
      borderRadius: 32,
      padding: "36px 44px",
      boxShadow: "0 30px 60px -30px rgba(30,24,19,0.18), 0 0 0 1px rgba(30,24,19,0.06)",
      display: "flex",
      flexDirection: "column",
      gap: 28,
      transform: `translateY(${(1 - visible) * 40}px)`,
      opacity: visible,
    }}
  >
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <span
          style={{
            width: 14,
            height: 14,
            borderRadius: 999,
            background: brand.success,
            boxShadow: `0 0 0 ${6 + Math.sin(frame / 6) * 4}px rgba(76,143,80,0.18)`,
          }}
        />
        <span
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 22,
            letterSpacing: 2,
            color: brand.muted,
            textTransform: "uppercase",
          }}
        >
          {call.status}
        </span>
      </div>
      <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 26, color: brand.ink }}>
        {mm}:{ss}
      </span>
    </div>

    <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
      <Avatar label={call.avatarLabel} frame={frame} />
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 32, fontWeight: 500, color: brand.ink, lineHeight: 1.1 }}>
          {call.caller}
        </div>
        <div style={{ fontSize: 24, color: brand.muted, marginTop: 4 }}>{call.subline}</div>
      </div>
      <Waveform frame={frame} fps={fps} />
    </div>

    <div
      style={{
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 22,
        color: brand.muted,
        lineHeight: 1.4,
        background: "rgba(30,24,19,0.04)",
        borderRadius: 16,
        padding: "16px 20px",
      }}
    >
      <Transcript frame={frame} lines={transcript} />
    </div>
  </div>
);

const Avatar: React.FC<{ label: string; frame: number }> = ({ label, frame }) => {
  const pulseScale = 1 + Math.sin(frame / 5) * 0.03;
  return (
    <div
      style={{
        width: 92,
        height: 92,
        borderRadius: 999,
        background: brand.accent,
        color: brand.cream,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Instrument Serif, serif",
        fontStyle: "italic",
        fontSize: 42,
        transform: `scale(${pulseScale})`,
      }}
    >
      {label}
    </div>
  );
};

const Waveform: React.FC<{ frame: number; fps: number }> = ({ frame }) => {
  const bars = 14;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, height: 72 }}>
      {Array.from({ length: bars }).map((_, i) => {
        const phase = frame / 4 + i * 0.7;
        const h = 16 + Math.abs(Math.sin(phase)) * 52;
        return (
          <div
            key={i}
            style={{
              width: 6,
              height: h,
              borderRadius: 4,
              background: brand.accent,
              opacity: 0.75,
            }}
          />
        );
      })}
    </div>
  );
};

const Transcript: React.FC<{ frame: number; lines: TranscriptLine[] }> = ({ frame, lines }) => {
  const visible = lines.filter((l) => frame >= l.at);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {visible.map((l, i) => (
        <div key={i} style={{ opacity: i === visible.length - 1 ? 1 : 0.6 }}>
          {l.text}
        </div>
      ))}
    </div>
  );
};

const TickerRow: React.FC<{
  label: string;
  value: string;
  progress: number;
  threshold: number;
  last?: boolean;
}> = ({ label, value, progress, threshold, last }) => {
  const visible = progress > threshold ? 1 : 0;
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "22px 0",
        borderBottom: last ? "none" : "1px solid rgba(30,24,19,0.08)",
        fontSize: 30,
        color: brand.ink,
        opacity: visible,
        transform: `translateX(${(1 - visible) * 20}px)`,
        transition: "all 0.3s",
      }}
    >
      <span style={{ fontFamily: "JetBrains Mono, monospace", color: brand.muted, fontSize: 26 }}>
        {label}
      </span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  );
};
