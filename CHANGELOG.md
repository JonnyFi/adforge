# Changelog

## 0.3.0 — 2026-04-21

Provider-neutral image generation, an in-place upgrade path for existing projects, and signed releases via OIDC. The v0.2.0 README already promised "any provider works" — this release actually delivers it.

### Added

- **Six built-in image providers.** Drop any one key into `.env` and generation works end-to-end: `BFL_API_KEY` (flux-2-max), `GEMINI_API_KEY` (gemini-2.5-flash-image / Nano Banana), `OPENAI_API_KEY` (gpt-image-1), `REPLICATE_API_TOKEN` (google/nano-banana-2), `STABILITY_API_KEY` (stable-image-core), `FAL_KEY` (fal-ai/flux/schnell). Auto-detection order: BFL → Google → OpenAI → Replicate → Stability → fal. Force a provider with `IMAGE_PROVIDER=<name>`, swap the default model per provider via `<PROVIDER>_MODEL`.
- **Provider dispatcher** (`engines/static/generate_hero.py`) — one entry point, dynamically loads the adapter matching the detected/pinned provider. Each adapter lives at `engines/static/image_providers/<name>.py`, stdlib-only, single `generate(prompt, width, height) -> bytes` contract. `engines/static/image_providers/CONTRACT.md` pins the contract; `flux.sh` is kept as a thin backcompat wrapper.
- **`image-provider-synth` skill** — when a user has a key for a provider adforge doesn't ship (Mistral, Ideogram, Azure OpenAI, Bedrock, Cloudflare Workers AI, self-hosted Comfy, …), the agent writes a new adapter from the provider's official docs. Docs-only rule (no training-data recall, no blog-post sources), verification date stamped in the header, shape-test pattern mirrors the built-ins.
- **`adforge upgrade` command** — pulls template changes from a newer CLI version into an existing project without clobbering local edits.
  - `init` now writes `.adforge/manifest.json` (SHA-256 per file + version) so upgrade can distinguish pristine template files from locally-edited ones.
  - Three-layer classification: **overwrite** (template authoritative — `.claude/skills/`, `engines/`, `adapters/`, `AGENTS.md`, …), **add-only** (starting points — `engines/static/examples/`, `variants/`), **skip** (user-owned — `brand.json`, `outputs/`, `.env`, …).
  - Edited overwrite-layer files get a `.new` sibling instead of being clobbered; the user diffs at their own pace.
  - `adforge upgrade --dry-run` previews without writing. Refuses to run outside an adforge project.
- **Signed releases via OIDC trusted publisher.** `.github/workflows/release.yml` triggers on `v*` tags, runs the test harness, and publishes to npm with `--provenance`. No `NPM_TOKEN` secret needed; provenance badge links every published tarball to its commit + workflow run.

### Changed

- **Setup flow onboards any provider.** `.claude/skills/setup/SKILL.md` walks through the full provider matrix with the exact dashboard URL per vendor, explains auto-detection order, and documents the `IMAGE_PROVIDER` pin. Flat-brand-color remains the zero-key fallback.
- **`new-campaign` + `composer-speccer` skills** check all six provider keys in the pre-flight and recommend `image-provider-synth` when the user brings a non-built-in provider.
- **Test harness** covers the dispatcher, BFL live shape, and mock-HTTP shape tests for all 5 newly-added providers — 46 assertions, CI-green on `--skip-motion`.

### Fixed

- v0.2.0 claimed provider-neutrality in the README but only BFL was actually wired. Claim now matches implementation.

## 0.2.0 — 2026-04-20

Breaks the "templates" paradigm. Layouts and motion compositions are now **reference implementations** the agent forks and adapts, not fixed templates every brand reskins. Also: proper font handling from day one, first-class custom + lookalike audiences, and a fallback path when users don't have a Meta token yet.

### Added

- **Motion primitives** (`engines/motion/src/primitives/`) — shared motion vocabulary (Kicker, Headline, Cursor, ClickRipple, Ticker, TypewriterField, ChromeOverlay). Compositions assemble from primitives instead of re-implementing them. New compositions stay structurally distinct instead of drifting into reskins.
- **Opt-in brand chrome** — declare wordmark or logo once in `brand.json → chrome.wordmark` (or leave it out). Both engines honor it via `apply_chrome` (PIL) / `<ChromeOverlay />` (Remotion).
  - Text wordmark: 6 corner positions (`top|bottom-left|center|right`), styles `serif-italic` / `sans-medium` / `mono-uppercase`, brand color roles.
  - Logo image: drop PNG/SVG under `assets/`, reference via `path`. `render.sh` auto-syncs `assets/` → `engines/motion/public/assets/` so the same path resolves in both engines.
  - Not opting in means naked canvas — right default for multi-angle testing.
- **Setup flow chrome step** — `.claude/skills/setup` now asks during onboarding: none / text / logo / "decide for me" (defaults to text wordmark). Per-locale prompt.
- **`motion-synth` skill** — mirror of `layout-synth` for motion. Reads video/GIF/storyboard references, drafts a new composition under `engines/motion/src/examples/` using primitives.
- **Font handling during setup.** Agent reads `font-family` from the user's website via Playwright, auto-downloads matching Google Fonts through the google-webfonts-helper API (returns TTF URLs directly, unlike CSS2), or falls back to the default trio (Instrument Serif / Inter / JetBrains Mono). `brand.json.fonts` now carries `serif_family` / `sans_family` / `mono_family` strings alongside filenames — same block drives PIL (filenames) and Remotion (`@font-face` injected in Root).
- **render.sh syncs `./fonts/`** to `engines/motion/public/fonts/` so Remotion's `staticFile()` resolves the same TTFs used by PIL.
- **Custom + lookalike audiences, plan-level.** `campaign-plan.json` gains an optional top-level `audiences` array — four types: `custom_list` (CSV, SHA-256 hashed client-side, 10k-row chunks), `pixel` (website retargeting, falls back to `META_PIXEL_ID`), `engagement` (page / post / IG / video), `lookalike` (seed by name within the plan, `country` + `ratio`). `deploy.py` creates each audience once, keyed by name in state, and resolves name references in `targeting.custom_audiences` / `targeting.excluded_custom_audiences` before any adset call.
- **Manual UI walk when `META_ACCESS_TOKEN` is missing.** `new-campaign` now documents a two-path flow: with token → `resolve.py` as usual; without token → step-by-step Ads Manager / Graph API Explorer walkthrough so interest IDs can be pasted back into the plan as `{id, name}` objects.

### Changed

- Renamed `engines/static/layouts/` → `engines/static/examples/`. Renamed `engines/motion/src/compositions/` → `engines/motion/src/examples/`. Auto-discovery behaves identically.
- README reframed around primitives + examples + chrome opt-in.
- `layout-synth` / `motion-synth` / `composer-speccer` / `new-campaign` skills updated to the new paths and architecture. Synth rules made non-negotiable: never modify an existing example to fit a new brief, never render brand chrome inline (layouts / compositions must leave chrome to `apply_chrome` / `<ChromeOverlay />`).
- Motion primitives + example compositions read `brand.fonts.serifFamily / sansFamily / monoFamily` instead of hardcoded CSS strings. Custom brand faces now actually render in motion instead of silently falling back to system serif/sans/mono.

### Fixed

- `assets/social-preview.png` now tracked so README image renders on GitHub.
- `stat-card` number→label overlap at certain font sizes.
- `shared.py::Brand.font` no longer crashes when a TTF is missing — logs a warning once per role and falls back to PIL's default font.
- `render.sh` now resolves variant + output paths to absolute before `cd`ing into the engine dir (previously broke when invoked with a relative `variants/...` path).
- `test/run-tests.sh` expected-paths list caught up with the `layouts/` → `examples/` and `compositions/` → `examples/` renames, plus new primitive + motion-synth files.

## 0.1.0 — 2026-04-12

Initial release. Static (PIL) + motion (Remotion) creative pipeline, Meta deploy adapter with idempotent state, brand tokens, agent skills (hub + new-campaign / add-creative / review-performance / setup).
