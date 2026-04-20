# Contributing

Thanks for poking at adforge. It's early — bugs and rough edges are expected, PRs to fix them are welcome.

## Ways to contribute

- **Bug reports** — open an issue with repro steps. Templates under `.github/ISSUE_TEMPLATE/`.
- **New engines** — drop a renderer in `templates/engines/`, register it in `adforge.config.json`. Skills pick it up automatically.
- **New adapters** — same pattern, but in `templates/adapters/`. Right now only Meta exists; TikTok / LinkedIn / Google would all slot in here.
- **Skill improvements** — the `.claude/skills/` markdown is the brain of the agent. Small wording tweaks can change the whole UX.

## Dev setup

```bash
git clone https://github.com/JonnyFi/adforge && cd adforge
npm link                              # makes `adforge` resolve to your checkout
./test/run-tests.sh --skip-motion     # run the harness
```

The test harness scaffolds a fresh project into `/tmp/adforge-tests`, fetches open-source fonts, renders a static advertorial, and (optionally) a motion render. It takes ~30s with `--skip-motion`, ~3min with full motion.

Requirements: Node 18+, Python 3 with Pillow, ffmpeg. Playwright is optional but recommended for brand extraction.

## Pull requests

- Branch off `main`.
- One PR per logical change. Small PRs are easier to review and ship.
- Run `./test/run-tests.sh --skip-motion` before opening the PR. CI runs it anyway, but failing locally first saves a round-trip.
- Commit messages: `fix(<area>): short line` or `feat(<area>): short line`, with a body explaining the *why* if non-obvious.
- Don't add Co-Authored-By trailers for trivial changes (typos, version bumps, formatting).

## What gets merged fast

- Bug fixes with a failing-then-passing test
- Documentation/README clarifications
- New engines / adapters that follow the existing registry pattern

## What needs a conversation first

- Breaking changes to scaffold structure
- New required API keys
- Changes to the skill prompts that alter agent behaviour in non-trivial ways

Open an issue with a proposal before spending time on any of those.

## Licence

MIT, same as the rest of the repo. By contributing, you agree your contribution is released under the same licence.
