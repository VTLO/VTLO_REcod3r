#!/usr/bin/env python3
"""VTLO_REcod3r — moteur d'analyse : que faut-il recoder en script plutôt que payer en tokens ?


Scans the skills / commands / prompts / memory files of Claude, Claude Code,
Gemini CLI, agy (Antigravity), Codex, Cursor (+ any folder / zip / ChatGPT or
Claude.ai export you point it at), scores every step as "rule" (code) or
"judgment" (AI), estimates the tokens you would save, picks the right language
for the replacement and generates the script + a thin stub that calls it.

Principle (from "Mon usage de l'IA"): if the rule fits in a few "if... then"
lines it is code; otherwise it is AI. Code drives the flow, the AI intervenes at
decision points, and its result is re-validated by code.

Read-only on your files. Pure standard library (Python >= 3.8, works in Termux).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = "1.0.0"
UNIMPL_MARK = "RECOD3R:A_IMPLEMENTER"
STATE_NAME = ".vtlo_recod3r"
MAX_FILE = 400_000          # bytes; bigger files are skipped
STUB_TOKENS = 80            # size of the thin stub that replaces an instruction body
OUT_TOKENS = 60             # typical compact stdout of a script
RESPONSE_TOKENS = 400        # assumed size of the model answer for a recurring chat prompt
STEP_OVERHEAD = 150         # tokens an AI spends per mechanical step (reasoning + tool call + result)
SECONDS_PER_KTOK = 1.5      # PDF: 2 000 tokens ~ 3 s
VERDICT_CODE, VERDICT_HYBRID, VERDICT_AI = "CODE", "HYBRID", "KEEP-AI"


def home() -> Path:
    return Path(os.environ.get("RECOD3R_HOME") or Path.home())


# --------------------------------------------------------------------------- tokens
def est_tokens(text: str) -> int:
    """Rough token estimate (chars / 3.8, +-15 %). Good enough to rank; not for billing."""
    return 0 if not text else max(1, round(len(text) / 3.8))


# --------------------------------------------------------------------------- parsing
FM_RX = re.compile(r"\A\ufeff?---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)


def parse_frontmatter(text: str):
    m = FM_RX.match(text)
    if not m:
        return {}, text
    meta, lines, i = {}, m.group(1).splitlines(), 0
    while i < len(lines):
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if km:
            k, v = km.groups()
            if v.strip() in (">", "|", ">-", "|-", ">+", "|+"):
                block, i = [], i + 1
                while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                    block.append(lines[i].strip())
                    i += 1
                meta[k] = " ".join(b for b in block if b)
                continue
            meta[k] = v.strip().strip("'\"")
        i += 1
    return meta, text[m.end():]


def parse_toml_command(text: str):
    """Gemini CLI custom command: description + prompt."""
    try:
        import tomllib  # py3.11+
        d = tomllib.loads(text)
        return str(d.get("description", "")), str(d.get("prompt", ""))
    except Exception:
        pass
    desc = re.search(r'^\s*description\s*=\s*"((?:[^"\\]|\\.)*)"', text, re.M)
    m = re.search(r'prompt\s*=\s*("""|\'\'\')(.*?)\1', text, re.S) or \
        re.search(r'prompt\s*=\s*(")((?:[^"\\]|\\.)*)"', text, re.S)
    return (desc.group(1) if desc else ""), (m.group(2) if m else text)


SECRET_RX = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}|AIza[0-9A-Za-z_\-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|"
    r"xox[baprs]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{16}|"
    r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}|"
    r"(?i:(?:api[_-]?key|token|secret|passw(?:or)?d)\s*[:=]\s*['\"]?[^\s'\"]{8,}))")


def redact(text: str) -> str:
    return SECRET_RX.sub("[REDACTED]", text)


# --------------------------------------------------------------------------- assets
@dataclass
class Asset:
    id: str
    agent: str
    kind: str            # memory | skill | command | agent | prompt | workflow | rules | recurring
    name: str
    path: str
    description: str
    body: str
    always: bool = False  # whole body loaded in every session
    has_scripts: bool = False
    tokens: int = 0
    desc_tokens: int = 0
    secrets: int = 0
    copies: int = 1
    extra: dict = field(default_factory=dict)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "asset"


def make_asset(agent, kind, path, text, always=False, has_scripts=False, name=None) -> Asset:
    path = str(path)
    desc = ""
    if path.endswith(".toml"):
        desc, body = parse_toml_command(text)
        meta = {}
    else:
        meta, body = parse_frontmatter(text)
        desc = str(meta.get("description", ""))
    if not name:
        name = str(meta.get("name") or "")
    if not name:
        p = Path(path)
        name = p.parent.name if p.name.upper() == "SKILL.MD" else (p.name if kind == "memory" else p.stem)
    asset_id = f"{agent}:{kind}:{_slug(name)}:{hashlib.sha1(path.encode()).hexdigest()[:5]}"
    a = Asset(asset_id, agent, kind, name, path, desc.strip(), body, always, has_scripts)
    a.tokens = est_tokens(body) + (0 if kind == "memory" else 0)
    a.desc_tokens = est_tokens(name + " " + desc) if kind in ("skill", "agent", "command") else 0
    a.secrets = len(SECRET_RX.findall(text))
    return a


def default_sources(cwd: Path):
    h, S = home(), []

    def add(agent, kind, base, pats, always=False):
        S.append((agent, kind, Path(base), pats, always))

    add("claude", "memory", h / ".claude", ["CLAUDE.md"], True)
    add("claude", "skill", h / ".claude/skills", ["*/SKILL.md"])
    add("claude", "command", h / ".claude/commands", ["**/*.md"])
    add("claude", "agent", h / ".claude/agents", ["**/*.md"])
    add("claude", "skill", h / ".claude/plugins", ["**/skills/*/SKILL.md"])
    add("claude", "command", h / ".claude/plugins", ["**/commands/*.md"])
    add("claude", "memory", cwd, ["CLAUDE.md", "CLAUDE.local.md"], True)
    add("claude", "skill", cwd / ".claude/skills", ["*/SKILL.md"])
    add("claude", "command", cwd / ".claude/commands", ["**/*.md"])
    add("claude", "agent", cwd / ".claude/agents", ["**/*.md"])
    add("gemini", "memory", h / ".gemini", ["GEMINI.md"], True)
    add("gemini", "command", h / ".gemini/commands", ["**/*.toml"])
    add("gemini", "skill", h / ".gemini/skills", ["*/SKILL.md"])
    add("gemini", "skill", h / ".gemini/extensions", ["*/skills/*/SKILL.md"])
    add("gemini", "command", h / ".gemini/extensions", ["*/commands/**/*.toml"])
    add("gemini", "memory", h / ".gemini/extensions", ["*/GEMINI.md"], True)
    add("gemini", "memory", cwd, ["GEMINI.md"], True)
    add("gemini", "command", cwd / ".gemini/commands", ["**/*.toml"])
    add("gemini", "skill", cwd / ".gemini/skills", ["*/SKILL.md"])
    add("agy", "skill", h / ".gemini/antigravity/skills", ["*/SKILL.md"])
    add("agy", "workflow", h / ".gemini/antigravity/global_workflows", ["*.md"])
    add("agy", "skill", cwd / ".agent/skills", ["*/SKILL.md"])
    add("agy", "workflow", cwd / ".agent/workflows", ["*.md"])
    add("agy", "rules", cwd / ".agent/rules", ["*.md"], True)
    add("codex", "memory", h / ".codex", ["AGENTS.md"], True)
    add("codex", "prompt", h / ".codex/prompts", ["*.md"])
    add("codex", "skill", h / ".codex/skills", ["*/SKILL.md"])
    add("codex", "memory", cwd, ["AGENTS.md"], True)
    add("shared", "skill", h / ".agents/skills", ["*/SKILL.md"])
    add("cursor", "rules", cwd / ".cursor/rules", ["*.mdc", "*.md"], True)
    return S


def _read(p: Path):
    try:
        if p.stat().st_size > MAX_FILE:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _has_scripts(skill_md: Path) -> bool:
    d = skill_md.parent
    if (d / "scripts").is_dir():
        return True
    try:
        return any(f.suffix in (".py", ".sh", ".js", ".mjs", ".ts", ".go", ".ps1") for f in d.iterdir())
    except OSError:
        return False


def collect_defaults(cwd: Path):
    out = []
    for agent, kind, base, pats, always in default_sources(cwd):
        if not base.exists():
            continue
        for pat in pats:
            try:
                files = sorted(base.glob(pat))
            except OSError:
                continue
            for f in files:
                if not f.is_file() or f.name.startswith("."):
                    continue
                t = _read(f)
                if t is None:
                    continue
                k = "skill" if f.name == "SKILL.md" else kind
                out.append(make_asset(agent, k, f, t, always, k == "skill" and _has_scripts(f)))
    return out


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def collect_extra(spec: str):
    """spec = PATH[:agent]. PATH may be a file, a folder or a .zip/.skill archive."""
    agent = "custom"
    p = spec
    m = re.match(r"^(.*):([a-z][a-z0-9_-]*)$", spec)
    if m and not re.match(r"^[A-Za-z]$", m.group(1)):  # avoid C:\ drive letters
        p, agent = m.group(1), m.group(2)
    path, out = Path(p).expanduser(), []
    if not path.exists():
        print(f"warning: {p} not found", file=sys.stderr)
        return out
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(("SKILL.md", ".md", ".toml", ".mdc")) and not n.endswith("/"):
                    info = z.getinfo(n)
                    if info.file_size > MAX_FILE:
                        continue
                    t = z.read(n).decode("utf-8", "replace")
                    k = "skill" if n.endswith("SKILL.md") else "prompt"
                    out.append(make_asset(agent, k, f"{path}!{n}", t, False, False))
        return out
    files = [path] if path.is_file() else []
    if path.is_dir():
        for root, dirs, fs in os.walk(path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".git")]
            if Path(root).relative_to(path).parts.__len__() > 6:
                continue
            for f in fs:
                if f.endswith((".md", ".mdc", ".toml", ".txt")):
                    files.append(Path(root) / f)
    for f in files:
        t = _read(f)
        if t is None:
            continue
        up = f.name.upper()
        if up == "SKILL.MD":
            kind, always = "skill", False
        elif up in ("CLAUDE.MD", "GEMINI.MD", "AGENTS.MD", "CLAUDE.LOCAL.MD"):
            kind, always = "memory", True
        elif f.suffix == ".toml":
            kind, always = "command", False
        else:
            kind, always = "prompt", False
        if kind == "prompt" and est_tokens(t) < 40:
            continue
        out.append(make_asset(agent, kind, f, t, always, kind == "skill" and _has_scripts(f)))
    return out


# --------------------------------------------------------------------------- lexicons
def _stems(words):
    return re.compile(r"(?<!\w)(?:" + "|".join(words) + r")\w*", re.I)


def _exact(words):
    return re.compile(r"(?<!\w)(?:" + "|".join(words) + r")(?!\w)", re.I)


MECH_VERBS = _stems([
    "pars", "extract", "extrai", "validat", "valid(?:er|ez|e)\\b", "convert", "format", "sort", "tri(?:er|ez|e)\\b",
    "filter", "filtr", "renam", "renomm", "count", "compt", "calculat", "calcul", "dedup", "dédoublon", "merg",
    "fusionn", "split", "divis", "grep", "diff", "lint", "execut", "exécut", "run\\b", "install", "compil", "deploy",
    "déploi", "copi", "mov(?:e|ing)\\b", "déplac", "delet", "supprim", "archiv", "upload", "download", "télécharg",
    "fetch", "schedul", "planifi", "normali[sz]", "sanitiz", "encod", "decod", "chmod", "mkdir", "rsync", "clone",
    "commit", "bump", "check\\b", "vérifi", "verif", "list(?:e|ing)?\\b", "lister", "scan", "trim", "strip", "replace",
    "remplac", "generat", "génér", "append", "ajout", "inject", "increment", "rotat", "compress", "unzip", "hash",
    "aggregat", "agrég", "group", "dump", "exit\\b", "abort", "skip", "drop", "print\\b", "emit", "affich", "ignor", "export", "import", "sync", "poll", "retry", "must output", "doit afficher",
])
MECH_NOUNS = _exact([
    "csv", "json", "yaml", "yml", "toml", "xml", "sql", "sqlite", "sha\\d*", "md5", "regex", "regexp", "git", "npm",
    "pip", "docker", "make", "curl", "http", "https", "api", "webhook", "stdout", "stderr", "stdin", "glob", "path",
    "chemin", "fichiers?", "files?", "folders?", "dossiers?", "directory", "répertoire", "exit code", "env",
    "ssh", "cli", "script", "batch", "cron", "logs?", "threshold", "seuil", "template", "gabarit", "placeholder",
    "timestamp", "semver", "changelog", "checksum", "port", "url", "endpoint", "pdf", "xlsx", "docx", "tsv",
])
JUDG_STEMS = _stems([
    "summar", "résum", "explain", "expliqu", "draft", "rédig", "rewrit", "réécri", "brainstorm", "creativ", "créati",
    "analy[sz]", "évalu", "evaluat", "recommend", "recommand", "decid", "décid", "judg", "jug(?:er|e)\\b", "critiq",
    "advis", "conseill", "persona", "empath", "nuanc", "interpr", "interprét", "reason", "raisonn", "understand",
    "compren", "comprend", "translat", "tradui", "traduc", "idea", "idée", "prioriti", "trade-?off", "strateg",
    "opinion", "feedback", "tutor", "teach", "enseign", "coach", "role-?play", "storytell", "narrat", "tone\\b",
    "voice", "ambig", "persuad", "convinc", "inspir", "brainstorm", "imagin", "propos(?:e|er)\\b", "suggest",
    "sugg[eé]r", "réfléchi", "think", "consider", "weigh", "pondér", "empathi", "engag", "style\\b", "writing",
    "écriture", "compose", "polish", "improve", "amélior", "tailor", "adapt",
])
JUDG_PHRASES = re.compile(
    r"(use your (?:best )?judg|as appropriate|if appropriate|selon le contexte|si pertinent|si nécessaire|"
    r"best practices?|bonnes pratiques|you are an?\b|you're an?\b|act as\b|tu es un|vous êtes un|agis comme|"
    r"expert in|spécialiste|senior\b.*\b(?:engineer|developer|ingénieur))", re.I)
COND_RX = re.compile(r"(?<!\w)(?:if|when|unless|otherwise|else|then|whenever|si|alors|sinon|lorsque|quand)(?!\w)", re.I)
FMT_RX = re.compile(r"(?i)\b(exactly|exact|strict(?:ly)?|schema|schéma|must (?:be|output|return)|format\s*:|"
                    r"doit (?:être|retourner|afficher)|one per line|par ligne|regex|json)\b")
CMD_RX = re.compile(
    r"^\s*(?:\$ |> |!`|!\{|(?:sudo\s+)?(?:git|npm|npx|pip3?|python3?|node|bash|sh|curl|wget|jq|rg|grep|sed|awk|find|"
    r"ls|cat|cp|mv|rm|mkdir|chmod|docker|make|cargo|go|gh|adb|ssh|scp|rsync|tar|unzip|zip|pnpm|yarn|uv|ruff|eslint|"
    r"prettier)\s)")

FAMILIES = {
    "json": r"\b(json|yaml|yml|toml|schema|manifest|package\.json|jsonl)\b",
    "tabular": r"\b(csv|tsv|excel|xlsx|spreadsheet|tableur|table|sql|sqlite|database|base de données|pivot|aggregat|group by)\b",
    "text": r"\b(logs?|grep|regex|lines?|lignes?|dedup|stack ?trace|output|sortie|sort|trier|filter|filtrer|parse)\b",
    "fs": r"\b(renam|renomm|folder|directory|dossier|répertoire|glob|move|déplac|copy|copier|archive|zip|backup|sauvegarde)\w*",
    "git": r"\b(git|commit|branch|pull request|PR|changelog|release|semver|pipeline|CI|pre-commit|hook)\b",
    "http": r"\b(api|http|https|webhook|endpoint|fetch|curl|rest|oauth|request|requête)\b",
    "code-analysis": r"\b(lint|ast|refactor|type ?check|formatter|prettier|ruff|eslint|dependenc|import|unused)\w*",
    "perf": r"\b(gigabytes?|million|large files?|gros fichiers?|performance|parallel|concurren|binary|binaire|stream|throughput)\b",
    "windows": r"\b(powershell|windows|registry|registre|\.ps1|active directory)\b",
    "browser": r"\b(scrap|browser|navigateur|playwright|selenium|click|clic|screenshot|dom)\w*",
    "doc": r"\b(docx|pdf|pptx|word|office|openpyxl|pypdf)\b",
    "security": r"\b(audit|hash|signature|cve|nmap|bluetooth|ble|crypto|secret|vulnerab|vulnérab|scan)\w*",
}
FAMILY_RX = {k: re.compile(v, re.I) for k, v in FAMILIES.items()}

# family -> ordered (language, why). First *available & suitable* wins.
FAMILY_LANG = {
    "json": [("jq", "JSON filter/transform in one line, nothing to maintain"),
             ("python", "stdlib json handles any non-trivial transform, zero deps")],
    "tabular": [("python", "csv + sqlite3 in the stdlib: group/sort/aggregate without installing anything"),
                ("duckdb", "SQL over CSV/Parquet when volumes grow")],
    "text": [("awk", "streaming line filters in a pipe, no interpreter start-up"),
             ("python", "re + generators: streaming, testable, readable when logic exceeds ~10 lines")],
    "fs": [("bash", "mv/cp/find/rsync are native; <=30 lines of glue"),
           ("python", "pathlib is cross-platform (Termux, Windows, macOS) and testable")],
    "git": [("bash", "git plumbing (rev-list, diff --numstat) composes natively"),
            ("python", "subprocess + parsing when the output needs real logic")],
    "http": [("python", "urllib (stdlib) or httpx: zero-dependency API calls with retries and timeouts"),
             ("node", "built-in fetch when the project is already JS/TS")],
    "code-analysis": [("existing-tool", "do not write a linter: orchestrate ruff / eslint / prettier / semgrep"),
                      ("bash", "thin wrapper running the existing tools and emitting a compact verdict")],
    "perf": [("go", "single static binary, goroutines, trivial cross-compile (linux/arm64, android, windows)"),
             ("rust", "when memory or latency is critical")],
    "windows": [("powershell", "native on Windows admin tasks (AD, registry, services)")],
    "browser": [("node", "Playwright first-class in Node/TS"),
                ("python", "Playwright for Python")],
    "doc": [("python", "python-docx / openpyxl / pypdf cover the Office/PDF ecosystem")],
    "security": [("python", "scapy / bleak / cryptography: fastest to a trustworthy audit tool"),
                 ("go", "static binary for field use")],
}
FAMILY_TOOLS = {
    "json": ["jq", "yq"], "tabular": ["sqlite3", "duckdb", "qsv"], "text": ["rg", "awk", "sort", "uniq"],
    "fs": ["fd", "rsync", "find"], "git": ["git", "pre-commit", "gitleaks", "git-cliff"], "http": ["curl", "http"],
    "code-analysis": ["ruff", "eslint", "prettier", "shellcheck", "semgrep"],
    "perf": ["rg", "hyperfine"], "doc": ["pandoc", "pdftotext", "libreoffice"],
    "security": ["gitleaks", "trivy", "nmap"], "browser": ["playwright"], "windows": ["pwsh"],
}
LANG_BIN = {"jq": "jq", "bash": "bash", "python": "python3", "node": "node", "go": "go", "rust": "cargo",
            "powershell": "pwsh", "awk": "awk", "duckdb": "duckdb", "existing-tool": "bash"}
SHELLISH = {"jq", "bash", "awk"}


def detect_env():
    env = {lang: bool(shutil.which(b) or (lang == "python" and shutil.which("python"))) for lang, b in LANG_BIN.items()}
    env["python"] = env["python"] or bool(sys.executable)
    tools = {t for ts in FAMILY_TOOLS.values() for t in ts}
    return {"langs": env, "tools": {t: bool(shutil.which(t)) for t in sorted(tools)}}


def recommend_language(text: str, n_code: float, env: dict):
    hits = {f: len(rx.findall(text)) for f, rx in FAMILY_RX.items()}
    generic = ("text", "fs")
    ranked = sorted((f for f, c in hits.items() if c > 0), key=lambda f: (f in generic, -hits[f]))
    fams = ranked[:2]
    cands, seen = [], set()
    for f in fams:
        for lang, why in FAMILY_LANG[f]:
            if lang in SHELLISH and n_code > 4 and env["langs"].get("python"):
                continue  # too much logic for a one-liner/glue script
            if lang not in seen:
                seen.add(lang)
                cands.append((lang, why, f))
    if not cands:
        cands = [("python", "default: stdlib only, readable, testable, runs everywhere (incl. Termux)", "generic")]
    cands.sort(key=lambda c: 0 if env["langs"].get(c[0], c[0] == "existing-tool") else 1)  # stable: keeps order otherwise
    primary = cands[0]
    existing = []
    for f in fams:
        for t in FAMILY_TOOLS.get(f, []):
            existing.append({"tool": t, "installed": env["tools"].get(t, False)})
    return {"primary": primary[0], "why": primary[1], "family": primary[2],
            "available": env["langs"].get(primary[0], primary[0] == "existing-tool"),
            "alternatives": [{"lang": c[0], "why": c[1]} for c in cands[1:3]],
            "existing_tools": existing[:6], "families": fams}


# --------------------------------------------------------------------------- analysis
def split_units(body: str):
    """Yield (text, in_fence) units: one per bullet/line/sentence; a fence yields <=3 units."""
    in_fence, fence_n = False, 0
    for raw in body.splitlines():
        s = raw.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            fence_n = 0
            continue
        if not s or s.startswith("#") and not in_fence:
            continue
        if in_fence:
            fence_n += 1
            if fence_n <= 3:
                yield s, True
            continue
        s = re.sub(r"^(?:[-*+]|\d+[.)]|\[[ xX]\])\s+", "", s)
        if len(s) > 220:
            for part in re.split(r"(?<=[.!?;:])\s+", s):
                if part.strip():
                    yield part.strip(), False
        else:
            yield s, False


def classify_unit(text: str, in_fence: bool) -> str:
    if in_fence or CMD_RX.match(text):
        return "code"
    verbs, nouns = len(MECH_VERBS.findall(text)), len(MECH_NOUNS.findall(text))
    j = len(JUDG_STEMS.findall(text)) + 2 * len(JUDG_PHRASES.findall(text))
    m = min(verbs, 3) + 0.5 * min(nouns, 3)
    if verbs >= 1 or nouns >= 2 or (nouns >= 1 and COND_RX.search(text)):
        if COND_RX.search(text):
            m += 0.5
        if FMT_RX.search(text):
            m += 0.5
    else:
        m = 0
    j = min(j, 3)
    if m == 0 and j == 0:
        return "neutral"
    if j == 0:
        return "code"
    if m == 0:
        return "ai"
    return "code" if m >= 2 * j else ("mixed" if m >= j else "ai")


def analyze_text(body: str):
    counts, code, ai, mixed = Counter(), [], [], []
    for u, f in split_units(body):
        c = classify_unit(u, f)
        counts[c] += 1
        if c == "code" and not f:
            code.append(u)
        elif c == "ai":
            ai.append(u)
        elif c == "mixed":
            mixed.append(u)
    n = counts["code"] + counts["ai"] + counts["mixed"]
    codeable = (counts["code"] + 0.5 * counts["mixed"]) / n if n else None
    return {"codeable": codeable, "n": n, "counts": counts, "code": code, "ai": ai, "mixed": mixed}


def verdict_for(codeable, n, min_n=3):
    if codeable is None or n < min_n:
        return VERDICT_AI, "low"
    conf = "high" if n >= 8 else "medium"
    if codeable >= 0.70:
        return VERDICT_CODE, conf
    if codeable >= 0.40:
        return VERDICT_HYBRID, conf
    return VERDICT_AI, conf


def _clip(s, n=110):
    s = re.sub(r"\s+", " ", redact(s)).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def analyze_asset(a: Asset, env: dict, P: dict, usage: dict):
    an = analyze_text(a.body)
    cnt = an["counts"]
    verdict, conf = verdict_for(an["codeable"], an["n"], 1 if a.kind == "recurring" else 3)
    n_code = cnt["code"] + cnt["mixed"] / 2
    lang = recommend_language(a.body + " " + a.description, n_code, env)
    r = {
        "id": a.id, "agent": a.agent, "kind": a.kind, "name": a.name, "path": a.path, "tokens": a.tokens,
        "desc_tokens": a.desc_tokens, "always": a.always, "secrets": a.secrets, "copies": a.copies,
        "codeable": None if an["codeable"] is None else round(an["codeable"], 2), "verdict": verdict,
        "confidence": conf, "n_code": cnt["code"], "n_mixed": cnt["mixed"], "n_ai": cnt["ai"],
        "code_steps": [_clip(x) for x in an["code"][:6]], "ai_steps": [_clip(x) for x in (an["ai"] + an["mixed"])[:6]],
        "lang": lang, "already_scripted": a.has_scripts,
        "uses_month": 0.0, "uses_src": "n/a", "save_per_use": 0, "save_month": 0, "payback_uses": None, "action": "keep",
    }
    if a.kind in ("memory", "rules"):
        code_tok = sum(est_tokens(x) for x in an["code"])
        r["memory_code_tokens"] = code_tok
        r["uses_month"], r["uses_src"] = P["sessions"], usage.get("sessions_src", "assumed")
        if code_tok >= 30 and verdict != VERDICT_AI or code_tok >= 60:
            r["verdict"] = "TRIM"
            r["save_per_use"] = code_tok
            r["save_month"] = code_tok * P["sessions"]
            r["action"] = "hooks"
        elif a.tokens > 1500:
            r["verdict"], r["action"] = "TRIM", "prune"
            r["save_per_use"] = int(a.tokens * 0.25)
            r["save_month"] = r["save_per_use"] * P["sessions"]
        else:
            r["verdict"] = VERDICT_AI
        return r
    # observed or assumed usage
    key = a.name.lower()
    tail = key.split(":")[-1]
    obs = usage.get("uses", {})
    if key in obs or tail in obs:
        r["uses_month"], r["uses_src"] = round(obs.get(key, obs.get(tail)), 1), "observed"
    elif a.kind == "recurring":
        r["uses_month"], r["uses_src"] = round(a.extra.get("per_month", 0), 1), "observed"
    else:
        r["uses_month"], r["uses_src"] = float(P["uses"]), "assumed"
    if verdict in (VERDICT_CODE, VERDICT_HYBRID) and (a.tokens >= 40 or a.kind == "recurring"):
        before = a.tokens + STEP_OVERHEAD * n_code + (RESPONSE_TOKENS if a.kind == "recurring" else 0)
        after = STUB_TOKENS + OUT_TOKENS + (1 - (an["codeable"] or 0)) * a.tokens
        r["save_per_use"] = int(max(0, before - after))
        r["save_month"] = int(r["save_per_use"] * r["uses_month"])
        onetime = 2500 + 2 * a.tokens
        r["payback_uses"] = math.ceil(onetime / r["save_per_use"]) if r["save_per_use"] else None
        r["action"] = "trim-body" if a.has_scripts else ("script" if verdict == VERDICT_CODE else "hybrid")
    return r


# --------------------------------------------------------------------------- duplicates
def _shingles(text, k=5):
    w = re.findall(r"\w+", text.lower())
    return {hash(tuple(w[i:i + k])) for i in range(max(0, len(w) - k + 1))}


def dedupe(assets):
    """Collapse byte-identical bodies (copies) and report near duplicates."""
    by_hash, uniq = {}, []
    for a in assets:
        h = hashlib.sha1(re.sub(r"\s+", " ", a.body).strip().encode()).hexdigest()
        if h in by_hash:
            by_hash[h].copies += 1
            by_hash[h].extra.setdefault("also", []).append(a.path)
        else:
            by_hash[h] = a
            uniq.append(a)
    near, cand = [], [(a, _shingles(a.body)) for a in uniq if a.tokens >= 60 and a.kind != "memory"][:1200]
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            (a, sa), (b, sb) = cand[i], cand[j]
            if not sa or not sb or min(len(sa), len(sb)) / max(len(sa), len(sb)) < 0.6:
                continue
            jac = len(sa & sb) / len(sa | sb)
            if jac >= 0.8:
                near.append({"a": a.id, "b": b.id, "a_name": f"{a.agent}/{a.name}", "b_name": f"{b.agent}/{b.name}", "similarity": round(jac, 2),
                             "tokens": min(a.tokens, b.tokens)})
    return uniq, near


# --------------------------------------------------------------------------- usage mining
def _skeleton(cmd: str) -> str:
    c = (cmd.strip().splitlines() or [""])[0][:200]
    c = re.sub(r'"[^"]*"|\'[^\']*\'', '"…"', c)
    c = re.sub(r"\b[0-9a-f]{7,40}\b", "<sha>", c)
    c = re.sub(r"(?<![\w-])(?:/|~/|\./)[\w./@+-]+", "<path>", c)
    c = re.sub(r"\b\d+\b", "<n>", c)
    return c


def mine_claude_code(days: int, root: Path | None = None):
    root = root or (home() / ".claude/projects")
    res = {"uses": {}, "commands": [], "sessions_src": "assumed", "files": 0}
    if not root.exists():
        return res
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    uses, cmds, stamps, sessions = Counter(), Counter(), [], 0
    for f in root.rglob("*.jsonl"):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) < cutoff:
                continue
            had = True
            with f.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if ('"Skill"' not in line and "command-name" not in line and '"Bash"' not in line):
                        continue
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    ts = o.get("timestamp")
                    try:
                        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    except ValueError:
                        t = None
                    if t and t < cutoff:
                        continue
                    if t:
                        stamps.append(t)
                    c = (o.get("message") or {}).get("content")
                    if isinstance(c, str):
                        for m in re.finditer(r"<command-name>/?([^<\s]+)</command-name>", c):
                            uses[m.group(1).lower()] += 1
                    elif isinstance(c, list):
                        for it in c:
                            if not isinstance(it, dict):
                                continue
                            if it.get("type") == "text":
                                for m in re.finditer(r"<command-name>/?([^<\s]+)</command-name>", it.get("text", "")):
                                    uses[m.group(1).lower()] += 1
                            elif it.get("type") == "tool_use":
                                inp = it.get("input") or {}
                                if it.get("name") == "Skill" and inp.get("skill"):
                                    uses[str(inp["skill"]).lower()] += 1
                                elif it.get("name") == "Bash" and inp.get("command"):
                                    cmds[_skeleton(str(inp["command"]))] += 1
            sessions += had
        except OSError:
            continue
    span = max(7, (max(stamps) - min(stamps)).days + 1) if stamps else days
    span = min(span, days)
    scale = 30.0 / span
    res["uses"] = {k: v * scale for k, v in uses.items()}
    res["commands"] = [{"skeleton": k, "count": v, "per_month": round(v * scale, 1)}
                       for k, v in cmds.most_common(60) if v >= 5 and len(k) > 6][:15]
    if sessions:
        res["sessions"] = round(sessions * scale)
        res["sessions_src"] = "observed"
    res["files"], res["span_days"] = sessions, span
    return res


def mine_export(path: str, min_count=3):
    """ChatGPT / Claude.ai export (conversations.json or the .zip) -> recurring user prompts."""
    p = Path(path).expanduser()
    data = None
    try:
        if p.is_file() and zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as z:
                names = [n for n in z.namelist() if n.endswith("conversations.json")]
                data = json.loads(z.read(names[0])) if names else None
        elif p.is_file():
            data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError, KeyError):
        data = None
    if not isinstance(data, list):
        print(f"warning: could not read export {path}", file=sys.stderr)
        return []
    msgs, times = [], []
    for conv in data:
        if not isinstance(conv, dict):
            continue
        if "mapping" in conv:                                  # ChatGPT
            for node in conv["mapping"].values():
                m = (node or {}).get("message") or {}
                if (m.get("author") or {}).get("role") == "user":
                    parts = (m.get("content") or {}).get("parts") or []
                    txt = " ".join(x for x in parts if isinstance(x, str))
                    if txt.strip():
                        msgs.append(txt)
                        if m.get("create_time"):
                            times.append(float(m["create_time"]))
        elif "chat_messages" in conv:                          # Claude.ai
            for m in conv["chat_messages"]:
                if m.get("sender") == "human" and (m.get("text") or "").strip():
                    msgs.append(m["text"])
    groups = defaultdict(list)
    for t in msgs:
        w = re.findall(r"[\wÀ-ÿ']+", t.lower())[:7]
        if len(w) >= 4:
            groups[" ".join(re.sub(r"\d+", "#", x) for x in w)].append(t)
    span_days = max(30.0, (max(times) - min(times)) / 86400) if len(times) > 1 else 30.0
    out = []
    for key, items in groups.items():
        if len(items) < min_count:
            continue
        sample = max(items, key=len)
        out.append((key, items, sample, span_days))
    out.sort(key=lambda x: -len(x[1]) * est_tokens(x[2]))
    return out[:25]


def recurring_assets(export_path, agent):
    out = []
    for key, items, sample, span in mine_export(export_path):
        a = make_asset(agent, "recurring", f"{export_path}#{key}", sample, False, False, name=key[:40])
        a.tokens = int(sum(est_tokens(i) for i in items) / len(items))
        a.extra = {"count": len(items), "per_month": len(items) * 30.0 / span, "sample": _clip(sample, 160)}
        out.append(a)
    return out



# --------------------------------------------------------------------------- rapport (données)
def fmt_n(n):
    return f"{int(round(n)):,}".replace(",", " ")


def build_report(assets, extra_assets, near, usage, P, env):
    items = [analyze_asset(a, env, P, usage) for a in assets + extra_assets]
    items.sort(key=lambda r: (-r["save_month"], r["name"]))
    saved = sum(r["save_month"] for r in items)
    always_tok = sum(a.tokens * a.copies for a in assets if a.always)
    dormant = []
    if usage.get("uses") is not None and usage.get("files"):
        used = set(usage["uses"]) | {k.split(":")[-1] for k in usage["uses"]}
        for r in items:
            if r["agent"] == "claude" and r["kind"] in ("skill", "command", "agent") and r["name"].lower() not in used and r["desc_tokens"]:
                dormant.append({"name": r["name"], "agent": r["agent"], "kind": r["kind"], "desc_tokens": r["desc_tokens"],
                                "save_month": r["desc_tokens"] * P["sessions"], "path": r["path"]})
        dormant.sort(key=lambda d: -d["desc_tokens"])
    secrets = [{"name": r["name"], "path": r["path"], "count": r["secrets"]} for r in items if r["secrets"]]
    copies = [{"name": a.name, "copies": a.copies, "paths": [a.path] + a.extra.get("also", []), "tokens": a.tokens}
              for a in assets if a.copies > 1]
    return {
        "version": VERSION, "generated": datetime.now().isoformat(timespec="seconds"), "params": P, "env": env,
        "totals": {"assets": sum(a.copies for a in assets) + len(extra_assets), "unique": len(assets) + len(extra_assets),
                   "always_loaded_tokens": always_tok, "saved_tokens_month": saved,
                   "saved_cost_month": round(saved * P["price"] / 1e6, 2),
                   "saved_minutes_month": round(saved / 1000 * SECONDS_PER_KTOK / 60, 1)},
        "items": items, "duplicates": {"copies": copies, "near": near}, "dormant": dormant,
        "commands": usage.get("commands", []), "secrets": secrets,
        "usage": {k: usage.get(k) for k in ("files", "span_days", "sessions", "sessions_src")},
    }



# --------------------------------------------------------------------------- squeeze
ANSI_RX = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\].*?(?:\x07|\x1b\\)")
KEY_RX = re.compile(r"(?i)\b(error|fail(?:ed|ure)?|exception|traceback|panic|fatal|denied|refused|timeout|warn(?:ing)?|"
                    r"assert|segfault|cannot|can't|unable|not found|E\d{3,5})\b|✗|✘|❌")


def squeeze(text: str, budget: int = 800) -> str:
    """Compact noisy command output: strip ANSI/progress, collapse repeats, keep errors + head/tail within a token budget."""
    text = ANSI_RX.sub("", text)
    lines = []
    for ln in text.replace("\r\n", "\n").split("\n"):
        if "\r" in ln:
            ln = ln.split("\r")[-1] or ln.split("\r")[-2]
        lines.append(ln.rstrip())
    out, prev, n = [], None, 0
    for ln in lines:
        norm = re.sub(r"\d+", "#", ln.strip())
        if ln.strip() and norm == prev:
            n += 1
            continue
        if n:
            out[-1] += f"  [×{n + 1}]"
            n = 0
        if not ln.strip() and out and not out[-1].strip():
            prev = None
            continue
        out.append(ln)
        prev = norm if ln.strip() else None
    if n:
        out[-1] += f"  [×{n + 1}]"
    while out and not out[-1].strip():
        out.pop()
    cap, total = int(budget * 3.8), sum(len(x) + 1 for x in out)
    if total <= cap:
        return "\n".join(out) + "\n"
    keys = [i for i, x in enumerate(out) if KEY_RX.search(x)]
    sel, size = set(), 0

    def add(i):
        nonlocal size
        if 0 <= i < len(out) and i not in sel:
            sel.add(i)
            size += len(out[i]) + 1

    for i in reversed(keys):                       # most recent errors first
        if size + len(out[i]) + 1 > cap * 0.6:
            break
        add(i)
    k = 0
    while k < len(out):
        before = size
        for i in (k, len(out) - 1 - k):
            if size + len(out[i]) + 1 <= cap and i not in sel:
                add(i)
        if size == before:
            break
        k += 1
    res, last = [], -1
    for i in sorted(sel):
        if i != last + 1:
            res.append(f"… [{i - last - 1} lines omitted] …")
        res.append(out[i])
        last = i
    if last < len(out) - 1:
        res.append(f"… [{len(out) - 1 - last} lines omitted] …")
    return "\n".join(res) + "\n"



# --------------------------------------------------------------------------- génération de scripts (squelettes)
PY_T = r'''#!/usr/bin/env python3
# RECOD3R-MANIFEST: @@MANIFEST@@
# RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
"""@@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ ».

Généré par VTLO_REcod3r @@VERSION@@ depuis @@SRC@@.

Contrat (obligatoire : c'est ce qui rend le script utilisable dans un pipeline) :
  entrées   arguments, fichiers ou stdin ; jamais d'invite interactive
  sortie    résultat compact sur stdout ; --json = UN objet JSON ; diagnostics sur stderr
  codes     0 ok · 1 contrôle échoué (message sur stderr) · 2 usage · 3 décision IA requise
  réponse   si l'IA a été sollicitée (code 3), elle répond via RECOD3R_AI_ANSWER (JSON) au relancement ;
            le script REVALIDE cette réponse avant de s'en servir
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SPEC = @@SPEC@@
ETAPES_IA = @@AI@@


def ia_requise(question: str, **contexte):
    """Rend la main à l'IA avec la question la plus étroite possible (code 3)."""
    print(json.dumps({"needs_ai": question, "context": contexte}, ensure_ascii=False))
    raise SystemExit(3)


def reponse_ia():
    brut = os.environ.get("RECOD3R_AI_ANSWER")
    return json.loads(brut) if brut else None


def executer(args) -> dict:
    # TODO : implémenter SPEC. Tant que ce n'est pas fait : repli sûr vers l'IA.
    ia_requise("script non implémenté : exécuter les étapes d'origine à la main", etapes=SPEC)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("entrees", nargs="*", help="fichiers / valeurs à traiter (stdin si absent)")
    ap.add_argument("--json", action="store_true", help="sortie JSON")
    a = ap.parse_args(argv)
    r = executer(a)
    print(json.dumps(r, ensure_ascii=False) if a.json else "\n".join(f"{k}: {v}" for k, v in r.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

SH_T = r'''#!/usr/bin/env bash
# RECOD3R-MANIFEST: @@MANIFEST@@
# RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
# @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@, depuis @@SRC@@).
# Contrat : 0 ok · 1 contrôle échoué (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout)
#           réponse de l'IA au relancement : variable RECOD3R_AI_ANSWER (JSON) — à REVALIDER.
set -euo pipefail
IFS=$'\n\t'

# Spec (étapes mécaniques extraites des instructions d'origine) :
@@SPEC@@

ia_requise() { local m="${1//\\/\\\\}"; m="${m//\"/\\\"}"; printf '{"needs_ai":"%s"}\n' "$m"; exit 3; }
usage() { echo "usage : ${0##*/} [--json] ENTREE..." >&2; exit 2; }

[ "$#" -ge 1 ] || [ ! -t 0 ] || usage
# TODO : implémenter la spec. En attendant : repli sûr vers l'IA.
ia_requise "script non implémenté : exécuter les étapes d'origine à la main"
'''

JS_T = r'''#!/usr/bin/env node
// RECOD3R-MANIFEST: @@MANIFEST@@
// RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
// @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@, depuis @@SRC@@).
// Contrat : 0 ok · 1 contrôle échoué (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout)
//           réponse de l'IA au relancement : variable RECOD3R_AI_ANSWER (JSON) — à REVALIDER.
import process from "node:process";

// Spec (étapes mécaniques extraites des instructions d'origine) :
const SPEC = @@SPEC@@;

const iaRequise = (question, contexte = {}) => {
  console.log(JSON.stringify({ needs_ai: question, context: contexte }));
  process.exit(3);
};

const args = process.argv.slice(2);
if (args.length === 0 && process.stdin.isTTY) { console.error("usage : @@SLUG@@.mjs [--json] ENTREE..."); process.exit(2); }
// TODO : implémenter SPEC. En attendant : repli sûr vers l'IA.
iaRequise("script non implémenté : exécuter les étapes d'origine à la main", { etapes: SPEC });
'''

GO_T = r'''// RECOD3R-MANIFEST: @@MANIFEST@@
// RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
// @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@, depuis @@SRC@@).
// Contrat : 0 ok · 1 contrôle échoué (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout)
// Compilation statique : CGO_ENABLED=0 go build -o @@SLUG@@ .   (GOOS=linux GOARCH=arm64 pour Android/Termux)
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
)

// Spec (étapes mécaniques extraites des instructions d'origine) :
var spec = []string@@SPEC@@

func iaRequise(q string) {
	b, _ := json.Marshal(map[string]any{"needs_ai": q, "context": map[string]any{"etapes": spec}})
	fmt.Println(string(b))
	os.Exit(3)
}

func main() {
	asJSON := flag.Bool("json", false, "sortie JSON")
	flag.Parse()
	_ = asJSON
	// TODO : implémenter spec. En attendant : repli sûr vers l'IA.
	iaRequise("script non implémenté : exécuter les étapes d'origine à la main")
}
'''

PS_T = r'''#!/usr/bin/env pwsh
# RECOD3R-MANIFEST: @@MANIFEST@@
# RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
# @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@, depuis @@SRC@@).
# Contrat : 0 ok · 1 contrôle échoué (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout)
[CmdletBinding()] param([Parameter(ValueFromRemainingArguments)][string[]]$Entrees, [switch]$Json)
Set-StrictMode -Version Latest; $ErrorActionPreference = 'Stop'
$Spec = @@SPEC@@
function IaRequise([string]$q) { @{ needs_ai = $q; context = @{ etapes = $Spec } } | ConvertTo-Json -Compress; exit 3 }
# TODO : implémenter la spec. En attendant : repli sûr vers l'IA.
IaRequise 'script non implémenté : exécuter les étapes d''origine à la main'
'''

LANG_TPL = {"python": ("py", PY_T), "bash": ("sh", SH_T), "node": ("mjs", JS_T), "go": ("go", GO_T), "powershell": ("ps1", PS_T)}
LANG_RUNNER = {"python": ["python3"], "bash": ["bash"], "node": ["node"], "go": ["go", "run"], "powershell": ["pwsh", "-File"]}
MARK_RX = re.compile(r"^\s*(?:#|//)\s*" + re.escape(UNIMPL_MARK), re.M)
MANIFEST_RX = re.compile(r"RECOD3R-MANIFEST:\s*(\{.*\})")


def read_manifest(script_text: str) -> dict:
    m = MANIFEST_RX.search(script_text)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except ValueError:
        return {}


def _spec_literal(lang, steps):
    steps = [redact(s) for s in steps] or ["(aucune étape mécanique détectée : lire l'asset d'origine)"]
    if lang == "bash":
        return "\n".join("#  - " + s.replace("\n", " ") for s in steps)
    if lang == "go":
        return "{" + ", ".join(json.dumps(s, ensure_ascii=False) for s in steps) + "}"
    if lang == "powershell":
        return "@(" + ", ".join("'" + s.replace("'", "''") + "'" for s in steps) + ")"
    return json.dumps(steps, ensure_ascii=False, indent=2)


def manifest_for(r: dict) -> dict:
    return {"v": 1, "entree": ["args", "fichier", "stdin"], "sortie": "json",
            "familles": r["lang"].get("families") or ["generique"], "ia": bool(r["ai_steps"])}


def runner_str(lang):
    return " ".join(LANG_RUNNER[lang])


def stub_bodies(a: Asset, r: dict, slug: str, script_rel: str, script_global: str, lang: str):
    """Textes de stubs légers (≈80 tokens) dans le format natif de chaque agent."""
    ai = r["ai_steps"]
    desc = (a.description or f"Exécute le script déterministe « {a.name} »")[:300].replace("\n", " ")
    runner = runner_str(lang)
    ai_block = "\n".join(f"  - {s}" for s in ai) if ai else "  - (aucun : le script fait tout le travail)"
    g = f"{runner} {script_global}"
    common = (f"- code 0 : rapporte le résultat.\n- code 1 : rapporte stderr et arrête.\n"
              f"- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec "
              f"`RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :\n{ai_block}\n")
    skill_body = (f"Exécute `{runner} {script_rel} <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie "
                  f"standard. Ne refais pas ses étapes à la main.\n{common}")
    out = {
        "skill": f"---\nname: {slug}\ndescription: {desc}\n---\n{skill_body}",
        "claude_command": (f"---\ndescription: {desc[:120]}\nallowed-tools: Bash({LANG_RUNNER[lang][0]}:*)\n---\n"
                           f"Résultat du script :\n!`{g} $ARGUMENTS`\n\nN'agis que sur cette sortie.\n{common}"),
        "gemini_toml": (f'description = {json.dumps(desc[:120], ensure_ascii=False)}\nprompt = """\nRésultat du script :\n'
                        f'!{{{g} {{{{args}}}}}}\n\nN\'agis que sur cette sortie.\n{common}"""\n'),
        "md_prompt": (f"---\ndescription: {desc[:120]}\n---\nExécute `{g} $ARGUMENTS` et lis UNIQUEMENT sa sortie standard "
                      f"(ne refais pas ses étapes à la main).\n{common}"),
    }
    out["agents_snippet"] = f"- `{slug}` : exécuter `{g}` ; ne jamais refaire ses étapes à la main (code 3 = décision requise).\n"
    return out


def native_stub(a: Asset, bodies: dict):
    """(contenu, remplaçable_sur_place) dans le format natif de l'asset."""
    p = a.path
    if "!" in p or any(x in p for x in ("/plugins/", "/extensions/", "/cache/", "\\plugins\\")):
        return None
    if a.kind == "skill":
        return bodies["skill"]
    if a.path.endswith(".toml"):
        return bodies["gemini_toml"]
    if a.kind == "command" and a.agent == "claude":
        return bodies["claude_command"]
    if a.kind in ("prompt", "workflow") and a.path.endswith(".md"):
        return bodies["md_prompt"]
    return None


def brief_text(a: Asset, r: dict, slug: str, lang: str, ext: str):
    steps = "\n".join(f"- {s}" for s in r["code_steps"]) or "- (voir l'original)"
    ai = "\n".join(f"- {s}" for s in r["ai_steps"]) or "- aucune"
    orig = redact(a.body)[:6000]
    alts = "\n".join(f"- {x['lang']} : {x['why']}" for x in r["lang"]["alternatives"]) or "- aucune"
    ex = ", ".join(e["tool"] + ("" if e["installed"] else " (absent)") for e in r["lang"]["existing_tools"]) or "aucun"
    return f"""# Brief de codage : transformer « {a.name} » en script de qualité professionnelle ({lang})

Tu l'écris UNE fois, d'un seul jet ; il tournera ensuite pour 0 token. Économie estimée : {fmt_n(r['save_month'])} tokens/mois
({fmt_n(r['save_per_use'])} par usage × {r['uses_month']:g}/mois, {r['uses_src']}). Amortissement après ~{r['payback_uses']} usages.

## Fichiers
- Script à compléter : `scripts/{slug}.{ext}` (squelette déjà prêt, contrat de codes de sortie inclus).
- Garde le manifeste `RECOD3R-MANIFEST` en tête (mets-le à jour si les entrées/sorties changent).
- **Supprime la ligne `{UNIMPL_MARK}`** quand le script est réellement implémenté : c'est le signal d'avancement lu par VTLO_REcod3r.

## Choix du langage
{lang} — {r['lang']['why']}
Alternatives :
{alts}
Outils existants à réutiliser plutôt que réinventer : {ex}

## Livrables
1. Le script complet (étapes « code » ci-dessous), qui respecte le contrat du squelette (0 ok · 1 échec · 2 usage · 3 décision IA).
2. Sortie `--json` = UN objet JSON compact ; sans `--json`, texte court (l'IA le lira : chaque token coûte).

## Exigences de qualité
- Déterministe : même entrée → même sortie. Idempotent. Aucune invite interactive. Délai maximal borné.
- Bibliothèque standard uniquement, sauf dépendance clairement justifiée.
- Flux : ne charge jamais un gros fichier entier en mémoire.
- Valide toutes les entrées ; en cas d'échec : une ligne sur stderr, code 1. Jamais `shell=True`, `eval`, `os.system`, ni secret en argument.
- Tout ce qui demande de la compréhension → `ia_requise(question, **contexte)` (code 3) avec la question la plus étroite possible.
  La réponse de l'IA revient par `RECOD3R_AI_ANSWER` : le script la REVALIDE (le code a le dernier mot).
- Ne modifie AUCUN autre fichier que le script de ce dossier.

## Étapes qui deviennent du code
{steps}

## Étapes qui restent à l'IA (points de décision)
{ai}

## Instructions d'origine (secrets masqués)
```
{orig}
```

## Quand tu as fini
Rien d'autre à lancer : pas de test, pas de commande. Passe à la tâche suivante.
"""


def unique_slug(a: Asset, used: set) -> str:
    slug = _slug(a.name)
    if slug in used:
        slug = f"{slug}-{_slug(a.agent)}"
    base, n = slug, 2
    while slug in used:
        slug, n = f"{base}-{n}", n + 1
    return slug


def write_scaffold(a: Asset, r: dict, workdir: Path, lang: str | None, used: set, slug: str | None = None):
    lang = lang or r["lang"]["primary"]
    if lang in ("jq", "awk", "existing-tool"):
        lang = "bash"
    if lang not in LANG_TPL:
        lang = "python"
    ext, tpl = LANG_TPL[lang]
    slug = slug or unique_slug(a, used)
    used.add(slug)
    d = workdir / slug
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    src = a.path.split("!")[-1] if "!" in a.path else a.path
    txt = (tpl.replace("@@SLUG@@", slug).replace("@@TITLE@@", a.name.replace('"', "'")).replace("@@VERSION@@", VERSION)
           .replace("@@SRC@@", Path(src).name).replace("@@SPEC@@", _spec_literal(lang, r["code_steps"]))
           .replace("@@AI@@", json.dumps(r["ai_steps"], ensure_ascii=False))
           .replace("@@MANIFEST@@", json.dumps(manifest_for(r), ensure_ascii=False)))
    script = d / "scripts" / f"{slug}.{ext}"
    script.write_text(txt, encoding="utf-8")
    script.chmod(0o755)
    (d / "BRIEF.md").write_text(brief_text(a, r, slug, lang, ext), encoding="utf-8")
    return {"slug": slug, "dir": str(d), "script": str(script), "ext": ext, "lang": lang}
