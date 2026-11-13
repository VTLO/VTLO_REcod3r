#!/usr/bin/env python3
"""Faux agent pour les tests : « implémente » la tâche en copiant une implémentation prête (tests/impl/<slug>.*)."""
import re, shutil, sys
from pathlib import Path
prompt = Path(sys.argv[1]).read_text(encoding="utf-8")
slug = re.search(r"« ([\w-]+) »", prompt).group(1)
cwd = Path.cwd()
base = slug.split("-agy")[0]
for impl in (Path(__file__).parent / "impl").glob(base + ".*"):
    dest = cwd / "scripts" / f"{slug}{impl.suffix}"
    if dest.exists():
        shutil.copy2(impl, dest)
        print("implémenté", dest)
