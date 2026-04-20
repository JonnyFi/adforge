import { Composition } from "remotion";
import { OpsConsole, type OpsConsoleVariant } from "./engines/OpsConsole";
import { ProductMockup, type MockupVariant } from "./engines/ProductMockup";
import { Walkthrough, type WalkthroughVariant } from "./engines/Walkthrough";

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

export const Root: React.FC = () => (
  <>
    <Composition
      id="ops-console"
      component={OpsConsole}
      {...base}
      defaultProps={{ variant: opsConsoleExample }}
    />
    <Composition
      id="product-mockup"
      component={ProductMockup}
      {...base}
      defaultProps={{ variant: productMockupExample }}
    />
    <Composition
      id="walkthrough"
      component={Walkthrough}
      {...base}
      defaultProps={{ variant: walkthroughExample }}
    />
  </>
);
