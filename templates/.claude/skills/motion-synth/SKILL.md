---
name: motion-synth
description: Backend skill — read a motion reference (video, GIF, or storyboard) and synthesize a new Remotion composition under engines/motion/src/examples/ using the shared primitives. Use when none of the existing example compositions match the brief.
---

# motion-synth

Turn a motion reference into an executable `engines/motion/src/examples/<Name>.tsx` — a Remotion composition specific to the current brand's brief. Built on the shared `primitives/` vocabulary so new compositions don't end up as reskins of `OpsConsole`.

## When to invoke

- User shows a video, GIF, or storyboard and says "I want a Reels like this".
- User describes a motion concept that doesn't fit the example compositions (`ops-console`, `product-mockup`, `walkthrough`) — e.g. a text-on-loop meme, a split-screen before/after, a data ticker stack, a typing-headline-with-annotation, an iPhone-in-hand walkthrough.
- An existing example is structurally close but you'd have to stuff new props into it. Fork into a new composition instead; don't parametrize existing ones into uselessness.

If one of the example compositions *does* match cleanly, hand back to `composer-speccer` to draft a variant JSON against the existing composition.

## Process

### 1. Read the reference

Actually watch it. Describe out loud, in the conversation:

- **Canvas + duration**: 9x16 Reels? 1x1 Feed motion? How many seconds?
- **Temporal rhythm**: frame-by-frame, what happens and when? "0–1s kicker fades in. 1–2s headline springs up. 2–5s ticker counts. 5–8s ticker fills. 8–9s brand outro."
- **Primary motion idiom**: is the motion *typographic* (text does the work), *UI-demo* (app/product mockup), *data-feed* (ticker/list reveal), or *footage-edit* (real-world clips strung together)?
- **What the viewer is meant to *see first*** at frame 0, and *remember* at the end.

Write this description in the chat before drafting code. It is the spec.

### 2. Map to primitives

Look at `engines/motion/src/primitives/index.ts`. Shipping primitives:

- `Kicker` — all-caps mono label, fade-in from frame 0
- `Headline` — serif "Plain. *italic.*" dual-line with spring-in
- `BrandOutro` — wordmark, end-of-video fade-in
- `Cursor` + `ClickRipple` — cursor/tap motion with target + click feedback
- `Ticker` — threshold-based row reveal (good for stacked data feeds)
- `TypewriterField` — typing-in form field

List which primitives your reference uses, which parts need new composition-specific components, and which parts are genuinely new motion patterns that might deserve a primitive of their own.

If you need a new primitive (e.g. `SplitScreen`, `CountUp`, `FootagePanel`), **argue for it first** in chat. A primitive is justified when it would be reused across 3+ compositions. Otherwise, keep it local to the new composition — don't pollute `primitives/`.

### 3. Propose a name + type

Short PascalCase filename: `AgentDemo.tsx`, `BeforeAfter.tsx`, `SlotTimeline.tsx`. Check `engines/motion/src/examples/` — don't collide.

Draft a `<Name>Variant` type: which fields does a variant JSON need to drive this composition? Use consistent names with existing examples where possible (`kicker`, `headline`, `headlineItalic`). Only invent new fields for genuinely new content slots.

Show the type + primitive usage list to the user and get sign-off before writing code.

### 4. Draft the composition

Template shape:

```tsx
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { brand } from "../brand";
import { Kicker, Headline, BrandOutro } from "../primitives";
// add only the primitives you use

export type SlotTimelineVariant = {
  kicker: string;
  headline: string;
  headlineItalic?: string;
  // ...composition-specific fields
};

export const SlotTimeline: React.FC<{ variant: SlotTimelineVariant }> = ({ variant }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: brand.cream, fontFamily: "Inter, sans-serif" }}>
      <div style={{ padding: "72px 72px 64px", display: "flex", flexDirection: "column", gap: 40, height: "100%" }}>
        <Kicker text={variant.kicker} />
        <Headline text={variant.headline} italic={variant.headlineItalic} />
        {/* composition-specific body */}
        <div style={{ flex: 1 }} />
        <BrandOutro />
      </div>
    </AbsoluteFill>
  );
};
```

Rules — non-negotiable:

- **Use primitives where they fit.** Don't re-implement `Kicker` / `Headline` / `Cursor` inline — every re-implementation is a future divergence bug.
- **Use `brand` from `../brand`** for colors and the wordmark. Don't hardcode hex or font strings. If the reference uses a color not in `brand.json`, ask whether to (a) extend `brand.json` or (b) use the closest existing role.
- **Stay inside one file.** Composition-specific sub-components (like `CallCard`, `BrowserChrome`, `StepStage`) live as locals inside the composition file. Only extract to `primitives/` when it would be used across 3+ compositions.
- **fps + durationInFrames come from `useVideoConfig()`**, not hardcoded constants. The Composition in `Root.tsx` owns the timing.
- **Respect the variant shape contract.** Every field a reader might want to change across brands should be a variant prop. Don't bury brand-specific copy inside the component.
- **Composition file only exports the component + its Variant type.** Keep it portable — a future consumer can import without side effects.

### 5. Register the composition in Root.tsx

```tsx
import { SlotTimeline, type SlotTimelineVariant } from "./examples/SlotTimeline";

const slotTimelineExample: SlotTimelineVariant = { /* ... */ };

<Composition
  id="slot-timeline"
  component={SlotTimeline}
  {...base}
  defaultProps={{ variant: slotTimelineExample }}
/>
```

The `id` is what `render.sh <variant> <id> <out>` takes on the command line. Match the kebab-case filename.

### 6. Test-render

```
./engines/motion/render.sh variants/_motion-synth-test.json slot-timeline outputs/motion/_synth-test.mp4
```

Extract a preview frame to view in-conversation:

```
ffmpeg -y -i outputs/motion/_synth-test.mp4 -ss 00:00:04 -vframes 1 outputs/motion/_synth-test_frame.png
```

Iterate on timing, sizes, and content order based on user feedback.

### 7. Hand off

Once approved:

- Delete `_motion-synth-test.json`.
- Tell `composer-speccer` the new composition is available, paste the `Variant` type + example variant.

## Rules

- **One composition per file.** Don't stuff two concepts into one `<Name>.tsx`.
- **Never modify an existing composition to fit a new brief.** Fork into a new file. Existing compositions are reference examples — bloating them dilutes both.
- **Never hardcode brand values in a new composition.** The whole point of this skill existing is that every brand needs its own motion, not a reskin.
- **Static reference images**: if the reference is a static image (not motion), this skill doesn't cover it — hand off to `layout-synth`.
- **No footage loading without project assets.** If the composition needs video clips or screenshots, ask the user to drop them under `engines/motion/public/<subdir>/` and reference via `staticFile("<subdir>/clip.mp4")`.

## Why this exists

Templates are reskin-generators: every brand that uses the same composition ends up looking the same. Primitives + synth is the opposite: shared motion grammar (kicker/headline/cursor/ticker), brand-specific composition on top. You are responsible for enforcing that distinction every time you synthesize a new composition.
