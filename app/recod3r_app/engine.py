"""Analyse : lecture des skills/prompts, classification « code vs IA », économie (tokens, €, durée)."""
import glob as _glob
import math
import os
import re
import shutil
import zipfile
from pathlib import Path

VERSION = "3.0.0"
MARK = "RECOD3R:A_IMPLEMENTER"
MAX_FILE = 400_000
STUB_TOKENS = 80.0
OUT_TOKENS = 60.0
STEP_OVERHEAD = 150.0
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target"}
ATTACHED = {"references", "resources", "assets", "templates", "examples"}

MECH_VERBS = ["pars", "extract", "extrai", "validat", r"valid(?:er|ez|e)\b", "convert", "format", "sort", r"tri(?:er|ez|e)\b", "filter", "filtr", "renam", "renomm", "count", "compt", "calculat", "calcul", "dedup", "dédoublon", "merg", "fusionn", "split", "divis", "grep", "diff", "lint", "execut", "exécut", r"run\b", "install", "compil", "deploy", "déploi", "copi", r"mov(?:e|ing)\b", "déplac", "delet", "supprim", "archiv", "upload", "download", "télécharg", "fetch", "schedul", "planifi", "normali[sz]", "sanitiz", "encod", "decod", "chmod", "mkdir", "rsync", "clone", "commit", "bump", r"check\b", "vérifi", "verif", r"list(?:e|ing)?\b", "lister", "scan", "trim", "strip", "replace", "remplac", "generat", "génér", "append", "ajout", "inject", "increment", "rotat", "compress", "unzip", "hash", "aggregat", "agrég", "group", "dump", r"exit\b", "abort", "skip", "drop", r"print\b", "emit", "affich", "ignor", "export", "import", "sync", "poll", "retry", "must output", "doit afficher"]
MECH_NOUNS = ["csv", "json", "yaml", "yml", "toml", "xml", "sql", "sqlite", r"sha\d*", "md5", "regex", "regexp", "git", "npm", "pip", "docker", "make", "curl", "http", "https", "api", "webhook", "stdout", "stderr", "stdin", "glob", "path", "chemin", "fichiers?", "files?", "folders?", "dossiers?", "directory", "répertoire", "exit code", "env", "ssh", "cli", "script", "batch", "cron", "logs?", "threshold", "seuil", "template", "gabarit", "placeholder", "timestamp", "semver", "changelog", "checksum", "port", "url", "endpoint", "pdf", "xlsx", "docx", "tsv"]
JUDG_STEMS = ["summar", "résum", "explain", "expliqu", "draft", "rédig", "rewrit", "réécri", "brainstorm", "creativ", "créati", "analy[sz]", "évalu", "evaluat", "recommend", "recommand", "decid", "décid", "judg", r"jug(?:er|e)\b", "critiq", "advis", "conseill", "persona", "empath", "nuanc", "interpr", "interprét", "reason", "raisonn", "understand", "compren", "comprend", "translat", "tradui", "traduc", "idea", "idée", "prioriti", "trade-?off", "strateg", "opinion", "feedback", "tutor", "teach", "enseign", "coach", "role-?play", "storytell", "narrat", r"tone\b", "voice", "ambig", "persuad", "convinc", "inspir", "imagin", r"propos(?:e|er)\b", "suggest", "sugg[eé]r", "réfléchi", "think", "consider", "weigh", "pondér", "empathi", "engag", r"style\b", "writing", "écriture", "compose", "polish", "improve", "amélior", "tailor", "adapt"]

I = re.I
RX_MECH_VERBS = re.compile(r"\b(?:%s)\w*" % "|".join(MECH_VERBS), I)
RX_MECH_NOUNS = re.compile(r"\b(?:%s)\b" % "|".join(MECH_NOUNS), I)
RX_JUDG_STEMS = re.compile(r"\b(?:%s)\w*" % "|".join(JUDG_STEMS), I)
RX_JUDG_PHR = re.compile(r"(use your (?:best )?judg|as appropriate|if appropriate|selon le contexte|si pertinent|si nécessaire|best practices?|bonnes pratiques|you are an?\b|you're an?\b|act as\b|tu es un|vous êtes un|agis comme|expert in|spécialiste|senior\b.*\b(?:engineer|developer|ingénieur))", I)
RX_COND = re.compile(r"\b(?:if|when|unless|otherwise|else|then|whenever|si|alors|sinon|lorsque|quand)\b", I)
RX_FMT = re.compile(r"\b(exactly|exact|strict(?:ly)?|schema|schéma|must (?:be|output|return)|format\s*:|doit (?:être|retourner|afficher)|one per line|par ligne|regex|json)\b", I)
RX_CMD = re.compile(r"^\s*(?:\$ |> |!`|!\{|(?:sudo\s+)?(?:git|npm|npx|pip3?|python3?|node|bash|sh|curl|wget|jq|rg|grep|sed|awk|find|ls|cat|cp|mv|rm|mkdir|chmod|docker|make|cargo|go|gh|adb|ssh|scp|rsync|tar|unzip|zip|pnpm|yarn|uv|ruff|eslint|prettier)\s)")
RX_SECRET = re.compile(r"""(sk-[a-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,}|(?:api[_-]?key|token|secret|password)\s*[:=]\s*['"]?[A-Za-z0-9_\-./+]{12,})""", I)
RX_BULLET = re.compile(r"^(?:[-*+]|\d+[.)]|\[[ xX]\])\s+")
RX_SENT = re.compile(r"[.!?;:]\s+")

FAMILIES = [
    ("json", r"\b(json|yaml|yml|toml|schema|manifest|jsonl)\b"),
    ("tabular", r"\b(csv|tsv|excel|xlsx|spreadsheet|tableur|table|sql|sqlite|database|base de données|pivot|aggregat)"),
    ("text", r"\b(logs?|grep|regex|lines?|lignes?|dedup|output|sortie|sort|trier|filter|filtrer|parse)\b"),
    ("fs", r"\b(renam|renomm|folder|directory|dossier|répertoire|glob|move|déplac|copy|copier|archive|zip|backup)"),
    ("git", r"\b(git|commit|branch|pull request|changelog|release|semver|pipeline)\b"),
    ("http", r"\b(api|http|https|webhook|endpoint|fetch|curl|rest|oauth|request|requête)\b"),
    ("security", r"\b(audit|hash|signature|cve|crypto|secret|vulnerab|vulnérab|scan)"),
    ("windows", r"\b(powershell|windows|registry|registre|\.ps1)\b"),
    ("doc", r"\b(docx|pdf|pptx|word|office)\b"),
]
FAMILIES_RX = [(k, re.compile(r, I)) for k, r in FAMILIES]


def rnd(x):
    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


def home():
    return Path(os.environ.get("RECOD3R_HOME") or os.environ.get("HOME") or os.environ.get("USERPROFILE") or ".")


def which(binary):
    return shutil.which(binary) is not None


def est_tokens(s):
    return 0.0 if not s else float(max(1, rnd(len(s) / 3.8)))


def redact(s):
    return RX_SECRET.sub("[SECRET MASQUÉ]", s)


def slug(s):
    o = ""
    for c in s.lower():
        if c.isalnum() and c.isascii():
            o += c
        elif not o.endswith("-"):
            o += "-"
    t = o.strip("-")
    return t[:60] if t else "script"


def default_params():
    return {"uses_per_month": 20.0, "users": 1.0, "eur_per_mtok": 2.8, "ai_sec_per_ktok": 1.5, "script_sec": 0.5, "extra": []}


def make_params(d=None):
    p = default_params()
    if isinstance(d, dict):
        for k in ("uses_per_month", "users", "eur_per_mtok", "ai_sec_per_ktok", "script_sec"):
            try:
                if k in d and d[k] is not None:
                    p[k] = float(d[k])
            except (TypeError, ValueError):
                pass
        if isinstance(d.get("extra"), list):
            p["extra"] = [str(x) for x in d["extra"]]
    return p


# ------------------------------------------------------------------ analyse d'un texte
def split_units(body):
    out, in_fence, fence_n = [], False, 0
    for raw in body.splitlines():
        s = raw.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence, fence_n = not in_fence, 0
            continue
        if not s or (s.startswith("#") and not in_fence):
            continue
        if in_fence:
            fence_n += 1
            if fence_n <= 3:
                out.append((s, True))
            continue
        s = RX_BULLET.sub("", s, count=1)
        if len(s) > 220:
            last = 0
            for m in RX_SENT.finditer(s):
                p = s[last:m.start() + 1].strip()
                if p:
                    out.append((p, False))
                last = m.end()
            p = s[last:].strip()
            if p:
                out.append((p, False))
        else:
            out.append((s, False))
    return out


def classify_unit(text, in_fence):
    if in_fence or RX_CMD.match(text):
        return "code"
    verbs = len(RX_MECH_VERBS.findall(text))
    nouns = len(RX_MECH_NOUNS.findall(text))
    j = len(RX_JUDG_STEMS.findall(text)) + 2 * len(RX_JUDG_PHR.findall(text))
    cond, fmt = bool(RX_COND.search(text)), bool(RX_FMT.search(text))
    m = min(verbs, 3) + 0.5 * min(nouns, 3)
    if verbs >= 1 or nouns >= 2 or (nouns >= 1 and cond):
        if cond:
            m += 0.5
        if fmt:
            m += 0.5
    else:
        m = 0.0
    j = float(min(j, 3))
    if m == 0.0 and j == 0.0:
        return "neutral"
    if j == 0.0:
        return "code"
    if m == 0.0:
        return "ai"
    if m >= 2.0 * j:
        return "code"
    if m >= j:
        return "mixed"
    return "ai"


def clip(s, n):
    t = " ".join(redact(s).split())
    return t if len(t) <= n else t[:n - 1] + "…"


def pick_lang(text):
    t = text.lower()
    win = os.name == "nt"
    if ("powershell" in t or ".ps1" in t or "windows" in t) and (which("pwsh") or win):
        return "powershell", "instructions orientées Windows / PowerShell"
    if which("python3") or which("python"):
        return "python", "Python présent : bibliothèque standard riche (json, csv, hashlib, http)"
    if which("node"):
        return "node", "Node.js présent : JSON et HTTP natifs"
    if win:
        return "powershell", "PowerShell est présent sur tout Windows"
    return "bash", "aucun autre runtime détecté : shell POSIX"


def analyze(a, p):
    code, ai, mixed = [], [], []
    for u, f in split_units(a["body"]):
        c = classify_unit(u, f)
        if c == "code":
            code.append((u, f))
        elif c == "ai":
            ai.append(u)
        elif c == "mixed":
            mixed.append(u)
    n_code, n_mixed, n_ai = len(code), len(mixed), len(ai)
    n = n_code + n_mixed + n_ai
    codeable = (n_code + 0.5 * n_mixed) / n if n > 0 else None
    verdict = "AI"
    if codeable is not None and n >= 3:
        verdict = "CODE" if codeable >= 0.70 else ("HYBRID" if codeable >= 0.40 else "AI")
    eff_code = n_code + n_mixed / 2.0
    c = codeable or 0.0
    before = a["tokens"] + STEP_OVERHEAD * eff_code
    after = STUB_TOKENS + OUT_TOKENS + (1.0 - c) * a["tokens"]
    save = max(before - after, 0.0) if verdict != "AI" and a["tokens"] >= 40.0 else 0.0
    lang, why = pick_lang("%s %s" % (a["body"], a["description"]))
    ft = ("%s %s" % (a["body"], a["description"])).lower()
    families = [k for k, rx in FAMILIES_RX if rx.search(ft)]
    convertible = save > 0.0 and not a["has_scripts"]
    return {
        "id": "%s:%s:%s" % (a["agent"], a["kind"], a["name"]), "slug": slug(a["name"]), "agent": a["agent"], "kind": a["kind"],
        "name": a["name"], "path": a["path"], "tokens": a["tokens"], "codeable": None if codeable is None else rnd(codeable * 100) / 100,
        "verdict": verdict, "n_code": n_code, "n_mixed": n_mixed, "n_ai": n_ai,
        "code_steps": [clip(s, 110) for s, f in code if not f][:6], "ai_steps": [clip(s, 110) for s in (ai + mixed)[:6]],
        "lang": lang, "lang_why": why, "before_tokens": float(rnd(before)), "after_tokens": float(rnd(after)), "save_per_use": float(rnd(save)),
        "payback_uses": int(math.ceil((2500.0 + 2.0 * a["tokens"]) / save)) if save > 0.0 else None,
        "ai_sec_per_use": before / 1000.0 * p["ai_sec_per_ktok"], "script_sec_per_use": after / 1000.0 * p["ai_sec_per_ktok"] + p["script_sec"],
        "convertible": convertible, "selected": convertible, "has_scripts": a["has_scripts"], "secrets": bool(RX_SECRET.search(a["body"])),
        "families": families,
    }


# ------------------------------------------------------------------ lecture des sources
def parse_frontmatter(text):
    t = text.lstrip("﻿")
    if not t.startswith("---"):
        return None, "", t
    rest = t[3:]
    end = rest.find("\n---")
    if end < 0:
        return None, "", t
    fm, body = rest[:end], rest[end + 4:].lstrip("\r\n")
    name, desc = None, ""
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("name:"):
            name = l[5:].strip().strip("\"'")
        elif l.startswith("description:"):
            v = l[12:].strip()
            if v == "" or v.startswith(">") or v.startswith("|"):
                parts = []
                while i + 1 < len(lines) and (lines[i + 1].startswith(" ") or lines[i + 1].startswith("\t")):
                    i += 1
                    parts.append(lines[i].strip())
                desc = " ".join(parts)
            else:
                desc = v.strip("\"'")
        i += 1
    return name, desc, body


def parse_toml_cmd(text):
    m = re.search(r'^description\s*=\s*"((?:[^"\\]|\\.)*)"', text, re.M)
    desc = m.group(1) if m else ""
    i = text.find('prompt = """')
    body = ""
    if i >= 0:
        r = text[i + 12:]
        j = r.find('"""')
        body = r[:j if j >= 0 else len(r)]
    return desc, body


def make_asset(agent, kind, name, path, text, has_scripts, refs):
    if path.endswith(".toml"):
        d, b = parse_toml_cmd(text)
        fname = None
    else:
        fname, d, b = parse_frontmatter(text)
    if not b.strip():
        return None
    return {"agent": agent, "kind": kind, "tokens": est_tokens(b) + est_tokens(d), "name": fname or name, "path": path,
            "description": d, "body": b, "has_scripts": has_scripts, "refs": refs}


def read(p):
    try:
        if p.stat().st_size > MAX_FILE:
            return None
        return p.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None


def skill_dir_info(md):
    d = md.parent
    sd = d / "scripts"
    has_scripts = sd.is_dir() and any(sd.iterdir())
    refs = []
    for sub in ("references", "resources", "assets", "templates", "examples"):
        try:
            refs += ["%s/%s" % (sub, e.name) for e in (d / sub).iterdir()]
        except OSError:
            pass
    return has_scripts, sorted(refs)[:60]


def sources(cwd):
    h = home()
    return [
        ("claude", "skill", h / ".claude/skills", ["*/SKILL.md"]), ("claude", "command", h / ".claude/commands", ["**/*.md"]),
        ("claude", "agent", h / ".claude/agents", ["**/*.md"]), ("claude", "skill", h / ".claude/plugins", ["**/skills/*/SKILL.md"]),
        ("claude", "command", h / ".claude/plugins", ["**/commands/*.md"]), ("claude", "skill", cwd / ".claude/skills", ["*/SKILL.md"]),
        ("claude", "command", cwd / ".claude/commands", ["**/*.md"]),
        ("gemini", "command", h / ".gemini/commands", ["**/*.toml"]), ("gemini", "skill", h / ".gemini/skills", ["*/SKILL.md"]),
        ("gemini", "skill", h / ".gemini/extensions", ["*/skills/*/SKILL.md"]), ("gemini", "command", cwd / ".gemini/commands", ["**/*.toml"]),
        ("agy", "skill", h / ".gemini/antigravity-cli/skills", ["*/SKILL.md"]), ("agy", "skill", h / ".gemini/antigravity-cli/plugins", ["*/skills/*/SKILL.md"]),
        ("agy", "skill", h / ".gemini/config/skills", ["*/SKILL.md"]), ("agy", "skill", h / ".gemini/skills", ["*/SKILL.md"]), ("agy", "skill", cwd / ".agents/skills", ["*/SKILL.md"]),
        ("agy", "skill", h / ".gemini/antigravity/skills", ["*/SKILL.md"]), ("agy", "workflow", h / ".gemini/antigravity/global_workflows", ["*.md"]),
        ("agy", "skill", cwd / ".agent/skills", ["*/SKILL.md"]), ("agy", "workflow", cwd / ".agent/workflows", ["*.md"]),
        ("codex", "prompt", h / ".codex/prompts", ["*.md"]), ("codex", "skill", h / ".codex/skills", ["*/SKILL.md"]),
        ("shared", "skill", h / ".agents/skills", ["*/SKILL.md"]),
    ]


def _glob_all(pattern):
    try:
        return sorted(_glob.glob(pattern, recursive=True, include_hidden=True))
    except TypeError:  # Python < 3.11
        return sorted(_glob.glob(pattern, recursive=True))


def from_file(agent, kind, base, f, out, seen):
    try:
        key = f.resolve()
    except OSError:
        key = f
    if key in seen:
        return
    seen.add(key)
    text = read(f)
    if text is None:
        return
    is_skill = f.name == "SKILL.md"
    if is_skill:
        hs, refs = skill_dir_info(f)
        name = f.parent.name
    else:
        try:
            rel = f.relative_to(base)
        except ValueError:
            rel = f
        name, hs, refs = str(rel.with_suffix("")).replace("/", ":").replace("\\", ":"), False, []
    a = make_asset(agent, "skill" if is_skill else kind, name, str(f), text, hs, refs)
    if a:
        out.append(a)


def walk(d, depth, out):
    if depth > 6:
        return
    try:
        entries = sorted(d.iterdir())
    except OSError:
        return
    for p in entries:
        if p.is_dir():
            if p.name not in SKIP_DIRS:
                walk(p, depth + 1, out)
        else:
            out.append(p)


def kind_from_path(p):
    comps = [c.lower() for c in p.parts]
    for k, v in (("commands", "command"), ("prompts", "prompt"), ("workflows", "workflow"), ("agents", "agent")):
        if k in comps:
            return v
    return None


def from_extra(spec, out, seen):
    p = Path(spec.strip().strip('"'))
    if p.suffix.lower() == ".zip" and p.is_file():
        try:
            z = zipfile.ZipFile(p)
        except (OSError, zipfile.BadZipFile):
            return
        names = z.namelist()
        for n in names:
            if not n.endswith("SKILL.md"):
                continue
            d = n[:-len("SKILL.md")]
            try:
                txt = z.read(n).decode("utf-8", errors="replace")
            except (KeyError, OSError):
                txt = ""
            refs = sorted(x[len(d):] for x in names if x.startswith(d) and not x.endswith("/") and not x.endswith("SKILL.md"))[:60]
            name = d.rstrip("/").rsplit("/", 1)[-1] or "skill"
            a = make_asset("extra", "skill", name, "%s!%s" % (p, n), txt, False, refs)
            if a:
                out.append(a)
        return
    if p.is_file():  # fichier choisi à la main : toujours accepté comme skill
        if p.suffix.lower() in (".md", ".mdc", ".txt", ".toml", ".markdown"):
            from_file("extra", "skill", p.parent, p, out, seen)
        return
    files = []
    walk(p, 0, files)
    for f in files:
        if any(c in ATTACHED for c in f.parts):
            continue
        if f.name == "SKILL.md":
            from_file("extra", "skill", p, f, out, seen)
        else:
            k = kind_from_path(f)
            if k and (f.name.endswith(".md") or f.name.endswith(".toml")):
                from_file("extra", k, p, f, out, seen)


def collect(cwd, extra):
    out, seen = [], set()
    for agent, kind, base, pats in sources(Path(cwd)):
        for pat in pats:
            for f in _glob_all("%s/%s" % (_glob.escape(str(base)), pat)):
                fp = Path(f)
                if fp.is_file():
                    from_file(agent, kind, base, fp, out, seen)
    for e in extra:
        if e.strip():
            from_extra(e, out, seen)
    return out


def analyze_all(assets, p):
    used = set()
    items = [analyze(a, p) for a in assets]
    for it in items:
        base = s = it["slug"]
        n = 2
        while s in used:
            s = "%s-%d" % (base, n)
            n += 1
        used.add(s)
        it["slug"] = s
    items.sort(key=lambda i: -i["save_per_use"])
    return items
