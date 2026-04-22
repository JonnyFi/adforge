# Changelog

## 0.3.2 — 2026-04-22

Follow-up critical fixes that were open after the 0.3.1 post-audit pass. Pulled
forward into this release instead of deferring to backlog: secret-leak risk in
error logs (#25), silent provider failures (#26), motion-pipeline drift (#27),
Meta adapter race/fragility (#29), and zero live API coverage (#31).

### Fixed

- **Access tokens no longer leak into error messages or query-string logs (#25).** All four Meta adapter modules now send `META_ACCESS_TOKEN` as an `Authorization: Bearer …` header instead of as `access_token=` in `params`/`data`. Error bodies pass through a shared `redact_body()` that strips `access_token` / `password` / `client_secret` / `appsecret_proof` values and truncates to 300 chars before hitting stderr. Image-provider modules now surface network errors as `(URLError)` / `(socket.timeout)` type names — full `{resp!r}` / `{pred!r}` dumps are gone so prompt text and nested keys don't spill into CI logs.
- **Image providers hand back bytes that are actually images (#26).** `generate_hero.py` validates the returned blob against PNG / JPEG / GIF / WebP magic bytes and rejects HTML error pages or truncated responses before writing to disk. The dispatcher also runs `inspect.signature` on each adapter's `generate()` to catch contract drift at load time. Replicate's default switched to `black-forest-labs/flux-schnell` (fast + cheap baseline). OpenAI gained an `OPENAI_QUALITY` env with `medium` default so iteration rounds don't accidentally burn "high" credits. BFL now snaps width/height into its supported `[256, 1440]` mult-of-32 range instead of 400 HTTP-ing on arbitrary sizes.
- **Meta adapter state survives concurrent runs and fails fast on bad accounts (#29).** `state_save()` writes through `tempfile.mkstemp` + `os.fsync` + `os.replace`, gated by an `fcntl.flock` on a sibling `.lock` file — no more partial-write corruption when two deploys race. State files carry a `_version: 1` stamp so older binaries refuse to clobber forward-incompatible state. A `_preflight_account()` check asserts `account_status == 1 (ACTIVE)` before any writes, and `_preflight_pixel()` resolves `META_PIXEL_ID` up front for plans that have `OFFSITE_CONVERSIONS` adsets. `upload_customer_file` detects input that's already a SHA-256 hex digest and skips re-hashing so pre-hashed audiences match on Meta's side.
- **Motion rendering is now CI-enforced (#27).** `release.yml` has a `motion-smoke` job that installs ffmpeg + chromium headless deps, `npm ci`s the motion template, and renders `variants/walkthrough-ci-smoke.json` end-to-end — asserting the resulting mp4 is >100KB. `publish` depends on it, so a broken Remotion pin, missing chromium dep, or ffmpeg regression blocks release. Remotion is now pinned to `^4.0.320` with a committed `package-lock.json`, and three placeholder screen PNGs ship at `engines/motion/public/screens/` so the default walkthrough renders out-of-the-box.
- **Live-API smoke workflow (#31).** New `.github/workflows/live-smoke.yml` runs weekly (Monday 06:00 UTC) and on-demand via `workflow_dispatch`. Six-provider matrix (`bfl`, `replicate`, `fal`, `openai`, `google`, `stability`) generates a 512×512 test image and asserts PNG/JPEG/WebP magic bytes on the output. Providers whose secret isn't set in the repo are skipped cleanly — so the workflow can exist on day one without all six keys. Catches model deprecations / auth format changes before users do.

## 0.3.1 — 2026-04-21

Post-release fix pass driven by a Karpathy-style 3-stage LLM council audit. Six criticals (Meta adapter compliance + rendering correctness) plus tooling hardening.

### Fixed

- **Meta Customer Audiences upload now conforms to Customer List Terms.** `adapters/meta/deploy.py::upload_customer_file` validates CSV headers against Meta's schema (`EMAIL/PHONE/FN/LN/CT/ST/ZIP/COUNTRY/DOBY/DOBM/DOBD/GEN/MADID/EXTERN_ID`), accepts German aliases (`vorname→FN`, `plz→ZIP`, `land→COUNTRY`, …), normalizes per-field before hashing (phone digits-only, name alpha-lowercase, ZIP first-5-for-US, COUNTRY ISO-2 lowercase, DOBM/DOBD zero-padded), and leaves `EXTERN_ID` unhashed. Unknown columns are rejected with a hint.
- **DSGVO consent gate on custom audience creation.** `ensure_audience()` refuses to create a `custom_list` audience unless the plan carries `"consent_confirmed": true`. Art. 6/7 GDPR compliance is not optional and can't be assumed from a CSV filename.
- **Video upload waits for Meta processing before creating the ad.** `Meta.upload_video()` polls `GET /{video_id}?fields=status` until `video_status=="ready"` (300s timeout, 4s interval). Previously the ad creative could reference a still-encoding video and fail silently.
- **Leads metric no longer triple-counts.** `adapters/meta/review.py` counts only the top-level `lead` action_type; Meta already rolls up `onsite_conversion.lead_grouped` and `offsite_conversion.fb_pixel_lead` into it.
- **Brand fonts actually render in Remotion.** `engines/motion/src/Root.tsx` previously injected `@font-face` as a sibling of `<Composition>` in `registerRoot()` — which never reaches the render iframe. Fonts now ship via a `withBrandFonts(...)` HOC wrapped around each `component={...}`, so `<style>` lives inside the composition tree.
- **BFL default model demoted to `flux-2-pro`.** `flux-2-max` is the flagship (billed accordingly); `flux-2-pro` is the mid-tier per CONTRACT.md:25 ("not the cheapest or the flagship"). Env var / docs / test harness aligned.
- **Radiant-gradient hero mode guards against missing brand block.** `engines/static/shared.py` warns and falls back to flat_brand_color when `hero_mode="radiant_gradient"` is set but `brand.json` has no `radiant_gradient` config. Previously crashed with `TypeError`.
- **Pillow version pinned** to `>=10.1.0,<12.0.0` in `engines/static/requirements.txt` to avoid the 10.0.x `ImageFont.load_default(size=)` regression.
- **Motion is 9:16-only**, per Meta's placement algorithm (Reels / Stories / Feed auto-crops). `new-campaign` skill and `motion-synth` skill updated. `phone-notifications` composition registered in `adforge.config.json`.

### Changed

- **`adforge doctor` checks for CLI updates.** Hits `https://registry.npmjs.org/adforge/latest` (2s timeout, swallows offline errors) and prints an upgrade hint when a newer version exists. Node major-version is now actually compared against the `>=18` floor instead of just being annotated.
- **`adforge init` refuses to scaffold into directories containing dotfiles.** Previously filtered `.` entries out of the emptiness check and could silently clobber pre-existing `.env.example`, `.gitignore`, or `.claude/`.
- **CLI overwrite layer now covers all motion root files** — `engines/motion/tsconfig.json`, `remotion.config.ts`, `src/index.ts`, `src/brand.ts(x)` — so `adforge upgrade` pulls framework-level changes instead of leaving projects on stale Remotion config.
- **Release workflow tightened.** Tag-vs-package.json guard moved before the test harness (fail fast on version mismatch). Trigger narrowed from `v*` to strict semver `v[0-9]+.[0-9]+.[0-9]+` so RC tags or typos don't accidentally publish.

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
