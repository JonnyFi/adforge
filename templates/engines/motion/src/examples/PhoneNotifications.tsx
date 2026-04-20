import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { brand } from "../brand";
import { ChromeOverlay } from "../primitives";

export type PhoneNotification = {
  at: number;
  time: string;
  title: string;
  body: string;
  badge?: string;
};

export type PhoneNotificationsVariant = {
  appName: string;
  lockscreenTime: string;
  lockscreenDate: string;
  notifications: PhoneNotification[];
  totalLabel?: string;
  totalAmount?: string;
  totalAt?: number;
};

export const PhoneNotifications: React.FC<{ variant: PhoneNotificationsVariant }> = ({
  variant,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const phoneIn = spring({ frame: frame - 10, fps, config: { damping: 22 } });
  const totalIn = spring({
    frame: frame - (variant.totalAt ?? 240),
    fps,
    config: { damping: 14, stiffness: 110 },
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${brand.cream} 0%, ${brand.creamAlt} 100%)`,
        fontFamily: "Inter, sans-serif",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <PhoneFrame
        visible={phoneIn}
        appName={variant.appName}
        time={variant.lockscreenTime}
        date={variant.lockscreenDate}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {variant.notifications.map((n, i) => (
            <NotificationCard key={i} notification={n} />
          ))}
        </div>
        {variant.totalLabel && variant.totalAmount && (
          <RunningTotal
            visible={totalIn}
            label={variant.totalLabel}
            amount={variant.totalAmount}
          />
        )}
      </PhoneFrame>
      <ChromeOverlay />
    </AbsoluteFill>
  );
};

const PHONE_W = 920;
const PHONE_H = 1800;

const PhoneFrame: React.FC<{
  visible: number;
  appName: string;
  time: string;
  date: string;
  children: React.ReactNode;
}> = ({ visible, appName, time, date, children }) => (
  <div
    style={{
      width: PHONE_W,
      height: PHONE_H,
      borderRadius: 72,
      background: brand.ink,
      padding: 12,
      boxShadow:
        "0 40px 100px rgba(15,15,18,0.35), inset 0 0 0 3px rgba(255,255,255,0.05)",
      transform: `translateY(${(1 - visible) * 40}px)`,
      opacity: visible,
    }}
  >
    <div
      style={{
        width: "100%",
        height: "100%",
        borderRadius: 60,
        background: "#111418",
        overflow: "hidden",
        position: "relative",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 22,
          left: "50%",
          transform: "translateX(-50%)",
          width: 180,
          height: 34,
          borderRadius: 18,
          background: brand.ink,
          zIndex: 2,
        }}
      />
      <div
        style={{
          padding: "92px 0 24px",
          textAlign: "center",
          color: "rgba(255,255,255,0.95)",
        }}
      >
        <div style={{ fontSize: 28, fontWeight: 300, letterSpacing: 2, opacity: 0.8 }}>
          {date}
        </div>
        <div
          style={{
            fontSize: 154,
            fontWeight: 200,
            lineHeight: 1,
            fontVariantNumeric: "tabular-nums",
            marginTop: 4,
          }}
        >
          {time}
        </div>
        <div
          style={{
            marginTop: 18,
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 20,
            letterSpacing: 2,
            opacity: 0.55,
            textTransform: "uppercase",
          }}
        >
          {appName}
        </div>
      </div>
      <div
        style={{
          flex: 1,
          padding: "0 22px 28px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-end",
          gap: 14,
        }}
      >
        {children}
      </div>
      <div
        style={{
          height: 8,
          width: 220,
          borderRadius: 4,
          background: "rgba(255,255,255,0.55)",
          margin: "0 auto 18px",
        }}
      />
    </div>
  </div>
);

const NotificationCard: React.FC<{ notification: PhoneNotification }> = ({ notification }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = spring({
    frame: frame - notification.at,
    fps,
    config: { damping: 18, stiffness: 110 },
  });
  if (t <= 0) return null;
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.14)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 24,
        padding: "18px 22px",
        display: "flex",
        alignItems: "flex-start",
        gap: 14,
        color: "white",
        opacity: t,
        transform: `translateY(${(1 - t) * 24}px) scale(${0.96 + t * 0.04})`,
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 14,
          background: brand.accent,
          color: brand.ink,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "Instrument Serif, serif",
          fontSize: 26,
          fontStyle: "italic",
          flexShrink: 0,
        }}
      >
        {notification.badge ?? "f"}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            gap: 10,
          }}
        >
          <div style={{ fontSize: 20, fontWeight: 600 }}>{notification.title}</div>
          <div
            style={{
              fontSize: 16,
              color: "rgba(255,255,255,0.55)",
              fontVariantNumeric: "tabular-nums",
              flexShrink: 0,
            }}
          >
            {notification.time}
          </div>
        </div>
        <div
          style={{
            fontSize: 19,
            color: "rgba(255,255,255,0.82)",
            marginTop: 2,
            lineHeight: 1.3,
          }}
        >
          {notification.body}
        </div>
      </div>
    </div>
  );
};

const RunningTotal: React.FC<{ visible: number; label: string; amount: string }> = ({
  visible,
  label,
  amount,
}) => (
  <div
    style={{
      marginTop: 14,
      padding: "20px 24px",
      borderRadius: 28,
      background: brand.accent,
      color: brand.ink,
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      opacity: visible,
      transform: `translateY(${(1 - visible) * 30}px) scale(${0.92 + visible * 0.08})`,
      boxShadow: "0 20px 50px rgba(255,225,74,0.35)",
    }}
  >
    <span
      style={{
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 18,
        letterSpacing: 2,
        textTransform: "uppercase",
        opacity: 0.8,
      }}
    >
      {label}
    </span>
    <span
      style={{
        fontFamily: "Instrument Serif, serif",
        fontSize: 56,
        fontVariantNumeric: "tabular-nums",
        lineHeight: 1,
      }}
    >
      {amount}
    </span>
  </div>
);
