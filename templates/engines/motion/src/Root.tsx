import { Composition } from "remotion";
import { withBrandFonts } from "./brand";
import { OpsConsole, type OpsConsoleVariant } from "./examples/OpsConsole";
import { ProductMockup, type MockupVariant } from "./examples/ProductMockup";
import { Walkthrough, type WalkthroughVariant } from "./examples/Walkthrough";
import {
  PhoneNotifications,
  type PhoneNotificationsVariant,
} from "./examples/PhoneNotifications";

const base = { fps: 30, width: 1080, height: 1920, durationInFrames: 270 };

const opsConsoleExample: OpsConsoleVariant = {
  kicker: "OPS CONSOLE · LIVE",
  headline: "Early morning.",
  headlineItalic: "The team is still asleep.",
  call: {
    status: "Call in progress",
    caller: "AI Agent",
    subline: "calling M. Smith · sick note",
    avatarLabel: "AI",
  },
  transcript: [
    { at: 45, text: "AI:  Good morning, this is the team. Everything okay?" },
    { at: 135, text: "MS:  I'm sick, can't make the shift today." },
    { at: 225, text: "AI:  Understood. Finding replacement, informing the team." },
  ],
  ticker: [
    { label: "05:02  Sick note", value: "M. Smith", threshold: 0.08 },
    { label: "05:04  Replacement", value: "A. Novak · available", threshold: 0.32 },
    { label: "05:05  Reassign", value: "Route 3 · 12 stops", threshold: 0.58 },
    { label: "05:06  Team notified", value: "✓ SMS sent", threshold: 0.84 },
  ],
};

const productMockupExample: MockupVariant = {
  kicker: "PRODUCT DEMO",
  headline: "Organise it.",
  headlineItalic: "In 20 seconds.",
  appName: "ExampleApp · Dashboard",
  navItems: ["Dashboard", "People", "Clients", "Billing"],
  activeNav: 0,
  targetButton: { x: 720, y: 480, label: "+ New item" },
  formFields: [
    { label: "Who", value: "M. Smith · Team 3" },
    { label: "When", value: "Mon, 20.04.2026" },
    { label: "Suggest", value: "A. Novak · available" },
  ],
  successMessage: "Team notified.\nAll set.",
};

const walkthroughExample: WalkthroughVariant = {
  kicker: "HOW IT WORKS",
  headline: "Three taps.",
  headlineItalic: "Done.",
  steps: [
    {
      image: "screens/step-1.png",
      imageWidth: 750,
      imageHeight: 1624,
      cursorFrom: { x: 680, y: 200 },
      cursorTo: { x: 670, y: 1355 },
      clickAt: 60,
      caption: "Open it",
      pointerStyle: "tap",
    },
    {
      image: "screens/step-2.png",
      imageWidth: 750,
      imageHeight: 1624,
      cursorFrom: { x: 120, y: 200 },
      cursorTo: { x: 375, y: 1440 },
      clickAt: 60,
      caption: "Do the thing",
      pointerStyle: "tap",
    },
    {
      image: "screens/step-3.png",
      imageWidth: 750,
      imageHeight: 1624,
      cursorFrom: { x: 100, y: 200 },
      cursorTo: { x: 600, y: 1530 },
      clickAt: 60,
      caption: "Confirm",
      pointerStyle: "tap",
    },
  ],
};

const phoneNotificationsExample: PhoneNotificationsVariant = {
  appName: "ExampleApp",
  lockscreenTime: "22:07",
  lockscreenDate: "Tuesday, 20 April",
  notifications: [
    { at: 30, time: "19:02", title: "Shift started", body: "Route 3 · 11 stops" },
    { at: 95, time: "19:14", title: "Stop 4/11", body: "+€11,20 earned" },
    { at: 160, time: "19:41", title: "Bonus unlocked", body: "+€18,00 · peak window" },
    { at: 220, time: "22:00", title: "Shift closed", body: "€94,80 · paid out" },
  ],
  totalLabel: "Tonight",
  totalAmount: "€94,80",
  totalAt: 240,
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="ops-console"
      component={withBrandFonts(OpsConsole)}
      {...base}
      defaultProps={{ variant: opsConsoleExample }}
    />
    <Composition
      id="product-mockup"
      component={withBrandFonts(ProductMockup)}
      {...base}
      defaultProps={{ variant: productMockupExample }}
    />
    <Composition
      id="walkthrough"
      component={withBrandFonts(Walkthrough)}
      {...base}
      defaultProps={{ variant: walkthroughExample }}
    />
    <Composition
      id="phone-notifications"
      component={withBrandFonts(PhoneNotifications)}
      {...base}
      defaultProps={{ variant: phoneNotificationsExample }}
    />
  </>
);
