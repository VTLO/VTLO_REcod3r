"""Build a fake multi-agent HOME for tests and demos: python3 tests/fixtures.py /tmp/fakehome"""
import json, sys, time
from pathlib import Path

CSV_SKILL = """---
name: csv-cleaner
description: Clean and validate CSV exports before import
---
# CSV cleaner
1. Parse the CSV file and validate that every row has the same number of columns.
2. Sort the rows by the `date` column and remove duplicate rows.
3. Convert all dates to ISO 8601 format (YYYY-MM-DD) exactly.
4. If a row has an empty `id`, then drop it and count it.
5. Write the cleaned file next to the original with the suffix `.clean.csv`.
6. Print a JSON summary: rows kept, rows dropped, duplicates removed.
```bash
python3 clean.py input.csv
```
"""
WRITER_SKILL = """---
name: brand-voice-writer
description: Write blog posts in the brand voice
---
You are an expert copywriter. Draft engaging articles in a warm, witty tone.
Brainstorm creative angles, then rewrite the introduction until it feels human.
Summarize the key idea in one sentence and adapt the style to the audience.
Use your best judgment to decide what is most persuasive and explain trade-offs.
Suggest three alternative titles and critique each one.
"""
PR_SKILL = """---
name: pr-review
description: Review a pull request
---
1. Run `git diff --stat main...HEAD` and list the changed files.
2. Run the linter and the test suite and check the exit code.
3. Count the lines added and removed per file and sort by size.
4. Analyze the design of the change and explain whether it is sound.
5. Evaluate the risks and recommend whether to merge.
6. Draft a friendly review comment with suggestions.
"""
CLAUDE_MD = """# Rules
- Always run prettier on every file you edit.
- Run the linter before every commit and fix the errors.
- Format dates as ISO 8601 and sort imports alphabetically.
- Never commit files larger than 1 MB, check with `git ls-files`.
- Be warm and explain your reasoning with nuance.
- Use your best judgment when the request is ambiguous.
""" + ("- Keep answers concise and friendly.\n" * 3)
GEMINI_TOML = '''description = "Rename photos"
prompt = """
For every file in the folder, rename it to YYYY-MM-DD_HHMM.jpg using the EXIF timestamp.
Sort the files by timestamp, skip duplicates by sha256 checksum and move them into one folder per month.
If the EXIF date is missing then use the file modification time.
Print the number of files renamed.
"""
'''
CODEX_PROMPT = """---
description: changelog
---
Collect the git commits since the last tag, group them by conventional commit type,
generate the CHANGELOG.md section, bump the semver version in package.json and print the diff.
If there are breaking changes then bump the major version.
"""


def build(root: Path):
    def w(rel, text):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p
    w(".claude/skills/csv-cleaner/SKILL.md", CSV_SKILL)
    w(".claude/skills/brand-voice-writer/SKILL.md", WRITER_SKILL)
    w(".claude/skills/pr-review/SKILL.md", PR_SKILL)
    w(".claude/skills/never-used/SKILL.md", CSV_SKILL.replace("csv-cleaner", "never-used").replace("Clean and", "Other:").replace("Parse the CSV","Read the CSV"))
    w(".claude/CLAUDE.md", CLAUDE_MD)
    w(".claude/commands/changelog.md", CODEX_PROMPT)
    w(".gemini/commands/rename-photos.toml", GEMINI_TOML)
    w(".gemini/antigravity/skills/csv-cleaner/SKILL.md", CSV_SKILL)          # exact copy across agents
    w(".gemini/antigravity/skills/csv-cleaner-v2/SKILL.md", CSV_SKILL.replace("Print a JSON summary", "Print a JSON report"))  # near dup
    w(".codex/prompts/changelog.md", CODEX_PROMPT)
    w(".codex/AGENTS.md", "Never store api_key = abcdef1234567890abcd in files.\nRun tests before commit.\n")
    # Claude Code transcripts
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    lines = []
    for i in range(30):
        lines.append(json.dumps({"timestamp": now, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "csv-cleaner"}}]}}))
    for i in range(6):
        lines.append(json.dumps({"timestamp": now, "message": {"role": "user", "content": "<command-name>/changelog</command-name>"}}))
    for i in range(12):
        lines.append(json.dumps({"timestamp": now, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": f"git log --oneline -n {i+5} --since=2026-01-{i+10:02d}"}}]}}))
    w(".claude/projects/-tmp-proj/session1.jsonl", "\n".join(lines) + "\n")
    # ChatGPT export with a recurring prompt
    convs = []
    for i in range(5):
        convs.append({"mapping": {"n1": {"message": {"author": {"role": "user"}, "create_time": 1760000000 + i * 86400 * 6,
            "content": {"parts": [f"Convertis ce tableau de {i+3} lignes en JSON puis trie par date et supprime les doublons: a,b,c {i}"]}}}}})
    w("chatgpt/conversations.json", json.dumps(convs))


if __name__ == "__main__":
    build(Path(sys.argv[1]))
