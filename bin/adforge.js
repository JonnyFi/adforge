#!/usr/bin/env node
/**
 * adforge CLI
 *
 * Subcommands:
 *   init <dir>          scaffold a new project
 *   upgrade [--dry-run] upgrade an existing project to the current CLI version
 *   doctor              check runtime deps (python, pillow, node, remotion)
 *   --version           print version
 *   --help              usage
 */

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execSync } = require("child_process");

const PKG = require("../package.json");
const TEMPLATES = path.join(__dirname, "..", "templates");

// Files shipped with the CLI where the agent owns the authoritative version.
// On upgrade we want the newer content — but never clobber local edits, so we
// fall back to a `.new` sibling whenever the local copy is modified.
const OVERWRITE_PREFIXES = [
  ".claude/skills/",
  ".claude/commands/",
  "engines/static/shared.py",
  "engines/static/compose.py",
  "engines/static/flux.sh",
  "engines/static/generate_hero.py",
  "engines/static/image_providers/",
  "engines/static/requirements.txt",
  "engines/motion/src/primitives/",
  "engines/motion/src/Root.tsx",
  "engines/motion/src/index.ts",
  "engines/motion/src/brand.ts",
  "engines/motion/src/brand.tsx",
  "engines/motion/tsconfig.json",
  "engines/motion/remotion.config.ts",
  "engines/motion/render.sh",
  "engines/motion/package.json",
  "adapters/meta/",
  "AGENTS.md",
  "README.md",
  ".env.example", // source is templates/env.example
  ".gitignore",   // source is templates/gitignore
];

// Examples are starting points — users fork / edit them. Copy on init, leave
// alone on upgrade. New examples shipped in later CLI versions are still added.
const ADD_ONLY_PREFIXES = [
  "engines/static/examples/",
  "engines/motion/src/examples/",
  "variants/",
];

// Anything not matching a prefix above is user-owned and never touched:
// brand.json, adforge.config.json, outputs/, .adforge/ (besides manifest),
// assets/, fonts/, .env, etc.

function log(msg) {
  process.stdout.write(msg + "\n");
}

function err(msg) {
  process.stderr.write(msg + "\n");
}

function usage() {
  log(`adforge v${PKG.version}

Usage:
  adforge init <project-dir>    Scaffold a new project
  adforge upgrade [--dry-run]   Upgrade an existing project to the current CLI version
  adforge doctor                Check runtime dependencies
  adforge --version             Print version
  adforge --help                Show this message

After init:
  cd <project-dir>
  cp .env.example .env          # fill in image-provider key, META_ACCESS_TOKEN, ...
  claude                        # or: codex

Then tell the agent: "start adforge"`);
}

function sha256OfFile(p) {
  return crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(s, d);
    } else {
      fs.copyFileSync(s, d);
    }
  }
}

function walkTemplateFiles() {
  // Returns [{ templatePath, projectRelPath }] for every file under TEMPLATES.
  // projectRelPath rewrites gitignore/env.example to .gitignore/.env.example
  // so it matches what init materialises on disk.
  const out = [];
  function walk(dir, relParts) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const abs = path.join(dir, entry.name);
      const parts = [...relParts, entry.name];
      if (entry.isDirectory()) {
        walk(abs, parts);
      } else {
        let rel = parts.join("/");
        if (rel === "gitignore") rel = ".gitignore";
        else if (rel === "env.example") rel = ".env.example";
        out.push({ templatePath: abs, projectRelPath: rel });
      }
    }
  }
  walk(TEMPLATES, []);
  return out;
}

function classifyPath(rel) {
  for (const p of OVERWRITE_PREFIXES) {
    if (rel === p || rel.startsWith(p)) return "overwrite";
  }
  for (const p of ADD_ONLY_PREFIXES) {
    if (rel === p || rel.startsWith(p)) return "add-only";
  }
  return "skip";
}

function writeManifest(projectDir, templateEntries) {
  const manifest = { version: PKG.version, files: {} };
  for (const { templatePath, projectRelPath } of templateEntries) {
    if (classifyPath(projectRelPath) === "skip") continue;
    manifest.files[projectRelPath] = sha256OfFile(templatePath);
  }
  const adforgeDir = path.join(projectDir, ".adforge");
  fs.mkdirSync(adforgeDir, { recursive: true });
  fs.writeFileSync(path.join(adforgeDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  fs.writeFileSync(path.join(adforgeDir, "version"), PKG.version + "\n");
}

function readManifest(projectDir) {
  const p = path.join(projectDir, ".adforge", "manifest.json");
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch (e) {
    return null;
  }
}

function cmdInit(targetDir) {
  if (!targetDir) {
    err("error: project directory required\n");
    usage();
    process.exit(2);
  }
  const abs = path.resolve(targetDir);
  if (fs.existsSync(abs)) {
    // Dotfiles count too — scaffolding writes .env.example, .gitignore, .claude/,
    // .adforge/ and would otherwise silently overwrite pre-existing ones.
    const entries = fs.readdirSync(abs);
    if (entries.length) {
      err(`error: ${abs} exists and is not empty`);
      process.exit(1);
    }
  }
  log(`scaffolding adforge project at ${abs}`);
  copyDir(TEMPLATES, abs);
  const gitignoreSrc = path.join(abs, "gitignore");
  if (fs.existsSync(gitignoreSrc)) {
    fs.renameSync(gitignoreSrc, path.join(abs, ".gitignore"));
  }
  const envExampleSrc = path.join(abs, "env.example");
  if (fs.existsSync(envExampleSrc)) {
    fs.renameSync(envExampleSrc, path.join(abs, ".env.example"));
  }
  writeManifest(abs, walkTemplateFiles());
  log(`
  done.

  next:
    cd ${path.relative(process.cwd(), abs) || "."}
    cp .env.example .env    # fill in API keys
    claude                  # or: codex

  in the agent: "start adforge"
`);
}

function cmdUpgrade(args) {
  const dryRun = args.includes("--dry-run");
  const projectDir = process.cwd();

  // Cheap sanity check — only run in something that looks like an adforge project.
  if (!fs.existsSync(path.join(projectDir, "adforge.config.json"))) {
    err(`error: not an adforge project (no adforge.config.json in ${projectDir})`);
    process.exit(1);
  }

  const manifest = readManifest(projectDir);
  const entries = walkTemplateFiles();

  const actions = { add: [], overwrite: [], newSibling: [], upToDate: [], skip: [] };

  for (const { templatePath, projectRelPath } of entries) {
    const cls = classifyPath(projectRelPath);
    const projectAbs = path.join(projectDir, projectRelPath);
    const exists = fs.existsSync(projectAbs);

    if (cls === "skip") {
      actions.skip.push(projectRelPath);
      continue;
    }

    if (!exists) {
      // File is new in this CLI version, regardless of layer — copy it in.
      actions.add.push({ projectRelPath, templatePath, projectAbs });
      continue;
    }

    if (cls === "add-only") {
      // Already there, user owns it — leave alone.
      actions.skip.push(projectRelPath);
      continue;
    }

    // Overwrite layer with existing local file: compare hashes.
    const templateHash = sha256OfFile(templatePath);
    const projectHash = sha256OfFile(projectAbs);
    if (templateHash === projectHash) {
      actions.upToDate.push(projectRelPath);
      continue;
    }

    const recordedHash = manifest && manifest.files ? manifest.files[projectRelPath] : null;
    if (recordedHash && recordedHash === projectHash) {
      // Local file is pristine at the recorded version — template moved, safe to overwrite.
      actions.overwrite.push({ projectRelPath, templatePath, projectAbs });
    } else {
      // Unknown or modified locally → write a .new sibling so the user can diff.
      actions.newSibling.push({ projectRelPath, templatePath, projectAbs });
    }
  }

  const fromVersion = manifest && manifest.version ? manifest.version : "unknown";
  log(`adforge upgrade: ${fromVersion} -> ${PKG.version}${dryRun ? "  (dry run)" : ""}`);
  log("");

  const print = (label, items, fmt) => {
    if (!items.length) return;
    log(`  ${label} (${items.length})`);
    for (const it of items) log(`    ${fmt(it)}`);
    log("");
  };

  print("add (new file)", actions.add, a => a.projectRelPath);
  print("overwrite (template moved, no local edits)", actions.overwrite, a => a.projectRelPath);
  print("review (local edits detected — writing .new sibling)", actions.newSibling, a => `${a.projectRelPath} -> ${a.projectRelPath}.new`);
  if (actions.upToDate.length) log(`  up-to-date: ${actions.upToDate.length} file(s)`);

  if (dryRun) {
    log("\n(dry run — no files written)");
    return;
  }

  for (const { templatePath, projectAbs } of actions.add) {
    fs.mkdirSync(path.dirname(projectAbs), { recursive: true });
    fs.copyFileSync(templatePath, projectAbs);
  }
  for (const { templatePath, projectAbs } of actions.overwrite) {
    fs.copyFileSync(templatePath, projectAbs);
  }
  for (const { templatePath, projectAbs } of actions.newSibling) {
    fs.copyFileSync(templatePath, projectAbs + ".new");
  }

  writeManifest(projectDir, entries);

  log(`\ndone. ${PKG.version} now recorded in .adforge/manifest.json.`);
  if (actions.newSibling.length) {
    log(`review ${actions.newSibling.length} .new file(s) and diff against your edited versions.`);
  }
}

async function checkLatestVersion() {
  // Node 18+ has global fetch. Swallow any network/parse error — doctor
  // is diagnostic, not blocking; a stale npm mirror shouldn't fail it.
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    const res = await fetch("https://registry.npmjs.org/adforge/latest", {
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (!res.ok) return;
    const { version } = await res.json();
    if (version && version !== PKG.version) {
      log(`  \u25cb adforge ${PKG.version} installed, ${version} available — npx adforge@latest upgrade`);
    }
  } catch (_) {
    // offline / blocked / aborted — stay quiet
  }
}

async function cmdDoctor() {
  const required = [
    { name: "node", cmd: "node --version", minMajor: 18 },
    { name: "python3", cmd: "python3 --version" },
    { name: "pip", cmd: "pip3 --version" },
    { name: "ffmpeg (for Remotion)", cmd: "ffmpeg -version" },
  ];
  const optional = [
    {
      name: "playwright (brand extraction)",
      cmd: "python3 -c \"import playwright\"",
      hint: "pip install playwright && playwright install chromium",
    },
  ];
  log("adforge doctor\n");
  let ok = true;
  for (const c of required) {
    try {
      const out = execSync(c.cmd, { stdio: ["ignore", "pipe", "ignore"] }).toString().split("\n")[0];
      if (c.minMajor) {
        const m = out.match(/(\d+)\.(\d+)\.(\d+)/);
        const major = m ? parseInt(m[1], 10) : null;
        if (major !== null && major < c.minMajor) {
          ok = false;
          log(`  \u2717 ${c.name.padEnd(32)} ${out} (need >=${c.minMajor})`);
          continue;
        }
      }
      log(`  \u2713 ${c.name.padEnd(32)} ${out}`);
    } catch (e) {
      ok = false;
      log(`  \u2717 ${c.name.padEnd(32)} not found`);
    }
  }
  for (const c of optional) {
    try {
      execSync(c.cmd, { stdio: ["ignore", "ignore", "ignore"] });
      log(`  \u2713 ${c.name.padEnd(32)} installed`);
    } catch (e) {
      log(`  \u25cb ${c.name.padEnd(32)} not installed (optional) — ${c.hint}`);
    }
  }
  await checkLatestVersion();
  log(ok ? "\nall required deps present." : "\nsome required deps missing — install them and retry.");
  process.exit(ok ? 0 : 1);
}

function main() {
  const [, , cmd, ...rest] = process.argv;
  switch (cmd) {
    case "init":
      return cmdInit(rest[0]);
    case "upgrade":
      return cmdUpgrade(rest);
    case "doctor":
      return cmdDoctor();
    case "--version":
    case "-v":
      log(`adforge ${PKG.version}`);
      return;
    case "--help":
    case "-h":
    case undefined:
      return usage();
    default:
      err(`unknown command: ${cmd}`);
      usage();
      process.exit(2);
  }
}

main();
