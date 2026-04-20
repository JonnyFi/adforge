# Changelog

## 0.2.0 — 2026-04-20

Breaks the "templates" paradigm. Layouts and motion compositions are now **reference implementations** the agent forks and adapts, not fixed templates every brand reskins.

### Added

- **Motion primitives** (`engines/motion/src/primitives/`) — shared motion vocabulary (Kicker, Headline, Cursor, ClickRipple, Ticker, TypewriterField, ChromeOverlay). Compositions assemble from primitives instead of re-implementing them. New compositions stay structurally distinct instead of drifting into reskins.
- **Opt-in brand chrome** — declare wordmark or logo once in `brand.json → chrome.wordmark` (or leave it out). Both engines honor it via `apply_chrome` (PIL) / `<ChromeOverlay />` (Remotion).
  - Text wordmark: 6 corner positions (`top|bottom-left|center|right`), styles `serif-italic` / `sans-medium` / `mono-uppercase`, brand color roles.
  - Logo image: drop PNG/SVG under `assets/`, reference via `path`. `render.sh` auto-syncs `assets/` → `engines/motion/public/assets/` so the same path resolves in both engines.
  - Not opting in means naked canvas — right default for multi-angle testing.
- **Setup flow chrome step** — `.claude/skills/setup` now asks during onboarding: none / text / logo / "decide for me" (defaults to text wordmark). Per-locale prompt.
- **`motion-synth` skill** — mirror of `layout-synth` for motion. Reads video/GIF/storyboard references, drafts a new composition under `engines/motion/src/examples/` using primitives.

### Changed

- Renamed `engines/static/layouts/` → `engines/static/examples/`. Renamed `engines/motion/src/compositions/` → `engines/motion/src/examples/`. Auto-discovery behaves identically.
- README reframed around primitives + examples + chrome opt-in.
- `layout-synth` / `motion-synth` / `composer-speccer` / `new-campaign` skills updated to the new paths and architecture. Synth rules made non-negotiable: never modify an existing example to fit a new brief, never render brand chrome inline (layouts / compositions must leave chrome to `apply_chrome` / `<ChromeOverlay />`).

### Fixed

- `assets/social-preview.png` now tracked so README image renders on GitHub.
- `stat-card` number→label overlap at certain font sizes.

## 0.1.0 — 2026-04-12

Initial release. Static (PIL) + motion (Remotion) creative pipeline, Meta deploy adapter with idempotent state, brand tokens, agent skills (hub + new-campaign / add-creative / review-performance / setup).
