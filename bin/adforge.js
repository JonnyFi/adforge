#!/usr/bin/env node
/**
 * adforge CLI
 *
 * Subcommands:
 *   init <dir>    scaffold a new project
 *   doctor        check runtime deps (python, pillow, node, remotion)
 *   --version     print version
 *   --help        usage
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const PKG = require("../package.json");
const TEMPLATES = path.join(__dirname, "..", "templates");

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
  adforge doctor                Check runtime dependencies
  adforge --version             Print version
  adforge --help                Show this message

After init:
  cd <project-dir>
  cp .env.example .env          # fill in BFL_API_KEY, META_ACCESS_TOKEN, ...
  claude                        # or: codex

Then tell the agent: "start adforge"`);
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

function cmdInit(targetDir) {
  if (!targetDir) {
    err("error: project directory required\n");
    usage();
    process.exit(2);
  }
  const abs = path.resolve(targetDir);
  if (fs.existsSync(abs)) {
    const entries = fs.readdirSync(abs).filter(n => !n.startsWith("."));
    if (entries.length) {
      err(`error: ${abs} exists and is not empty`);
      process.exit(1);
    }
  }
  log(`scaffolding adforge project at ${abs}`);
  copyDir(TEMPLATES, abs);
  // Rename dotfiles that npm strips
  const gitignoreSrc = path.join(abs, "gitignore");
  if (fs.existsSync(gitignoreSrc)) {
    fs.renameSync(gitignoreSrc, path.join(abs, ".gitignore"));
  }
  const envExampleSrc = path.join(abs, "env.example");
  if (fs.existsSync(envExampleSrc)) {
    fs.renameSync(envExampleSrc, path.join(abs, ".env.example"));
  }
  log(`
  done.

  next:
    cd ${path.relative(process.cwd(), abs) || "."}
    cp .env.example .env    # fill in API keys
    claude                  # or: codex

  in the agent: "start adforge"
`);
}

function cmdDoctor() {
  const required = [
    { name: "node", cmd: "node --version", min: "18" },
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
  log(ok ? "\nall required deps present." : "\nsome required deps missing — install them and retry.");
  process.exit(ok ? 0 : 1);
}

function main() {
  const [, , cmd, ...rest] = process.argv;
  switch (cmd) {
    case "init":
      return cmdInit(rest[0]);
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
