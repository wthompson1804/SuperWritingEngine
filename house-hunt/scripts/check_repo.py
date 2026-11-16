"""Repository hygiene check. Read-only: it writes nothing, fetches nothing and is not a pipeline stage.

  python3 scripts/check_repo.py                 all five checks
  python3 scripts/check_repo.py --include-raw   also look under raw/ for the exact value of the local Census key
  python3 scripts/check_repo.py --max 40        list at most 40 rows per check (default 60; 0 = no limit)

Checks
  1. files over 5 MB tracked in git (size from disk)
  2. CSVs under data/ that no script reads or writes: neither the file name, nor its numbered family
     ("live_check_batch_7.csv" counts when "live_check_batch_" is named), nor its folder is named in scripts/
  3. scripts no other file references (no import, no mention in another script, in run_all.py or in a document).
     A script that is run by hand shows up here unless a document names it: that is the point.
  4. documents that name a file which does not exist (paths in the text that start with data/, docs/, scripts/,
     site/, out/, seeds/ or raw/; patterns with * < > { } are skipped)
  5. strings that look like an API key or token, anywhere outside raw/ and .git. Only the file, the line number and
     the kind of match are printed. The value is never printed.

Exit code: 0 always (this is a report for a person to read, not a gate).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIG = 5 * 1024 * 1024
MAX = 60
PREFIXES = ("data", "docs", "scripts", "site", "out", "seeds", "raw")
TEXT_EXT = {".py", ".js", ".md", ".txt", ".csv", ".json", ".jsonl", ".html", ".htm", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sh",
            ".geojson", ".log", ".env", ""}

SECRET_PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("sk- style key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{24,}")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{6,}")),
    ("key or token in a URL", re.compile(r"[?&](?:key|api_key|apikey|api-key|access_token|token|auth|client_secret|subscription-key)=(?!DEMO_KEY)[A-Za-z0-9_\-\.%]{16,}", re.I)),
    ("key or token assigned in text", re.compile(r"(?:api[_\-]?key|apikey|secret|token|passwd|password|authorization|bearer)[\"']?\s*[:=]\s*[\"']?(?!DEMO_KEY)[A-Za-z0-9_\-\.]{24,}", re.I)),
    ("40 hex characters beside the word key", re.compile(r"(?i)key[^\n]{0,40}\b[0-9a-f]{40}\b|\b[0-9a-f]{40}\b[^\n]{0,40}key")),
]
# one cheap test per line before the patterns above are tried
MAYBE = re.compile(r"key|token|secret|passw|auth|bearer|AKIA|AIza|eyJ|gh[pousr]_|github_pat_|xox[baprs]-|sk-|PRIVATE", re.I)
# words that look like an assignment and are not a secret (a column name, a function call, a placeholder)
NOT_A_SECRET = re.compile(r"(?i)(?:token|key|secret|password)[\"']?\s*[:=]\s*[\"']?(?:os\.environ|census_key|lib\.|redact|None|null|true|false|not_found|unknown|required|optional)")


def sh(*args):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return r.stdout


def tracked():
    out = sh("git", "ls-files", "-z", ".")
    return [p for p in out.split("\0") if p]


def read(p: Path, limit=40 * 1024 * 1024):
    try:
        if p.stat().st_size > limit:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def show(rows, fmt=lambda r: r):
    rows = list(rows)
    for r in rows[:MAX or None]:
        print("  " + fmt(r))
    if MAX and len(rows) > MAX:
        print(f"  ... and {len(rows) - MAX} more (run with --max 0 for all)")
    if not rows:
        print("  none")


def script_files():
    return sorted(p for p in (ROOT / "scripts").rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py", ".js"))


def doc_files():
    docs = sorted((ROOT / "docs").rglob("*.md")) if (ROOT / "docs").exists() else []
    extra = [ROOT / n for n in ("README.md", "CLAUDE.md", "PROGRESS.md", "scripts/README.md")]
    return docs + [p for p in extra if p.exists()]


def check_big(files):
    print(f"\n== 1. Tracked files over {BIG // (1024 * 1024)} MB ==")
    rows = []
    for f in files:
        p = ROOT / f
        if p.is_file() and p.stat().st_size > BIG:
            rows.append((p.stat().st_size, f))
    rows.sort(reverse=True)
    total = sum(s for s, _ in rows)
    print(f"  {len(rows)} files, {total / 1e6:.1f} MB in all")
    show(rows, lambda r: f"{r[0] / 1e6:7.1f} MB  {r[1]}")


def family(name: str) -> str:
    """'live_check_batch_7.csv' -> 'live_check_batch_'; 'ratings_census_part_2.csv' -> 'ratings_census_part_'; else ''."""
    m = re.match(r"^(.*?_(?:batch|part|round)_?)[0-9a-z_]*\.csv$", name)
    if m:
        return m.group(1)
    m = re.match(r"^(.*?[_-])\d+[a-z]?\.csv$", name)
    return m.group(1) if m else ""


def check_csvs():
    print("\n== 2. CSVs under data/ that no script names (by file name, numbered family or folder) ==")
    code = "\n".join(read(p) for p in script_files() if p.name != "check_repo.py")
    rows, by_folder = [], 0
    csvs = sorted(p for p in (ROOT / "data").rglob("*.csv"))
    for p in csvs:
        rel = p.relative_to(ROOT)
        name, fam, stem = p.name, family(p.name), p.stem
        if name in code or (fam and fam in code):
            continue
        # a name assembled in code, for example f"{stem}.csv" or DATA / (key + ".csv"): the bare stem in quotes
        if re.search(r"[\"'/]" + re.escape(stem) + r"[\"'.]", code):
            continue
        parent = p.parent.name
        if parent not in ("data", "reference") and re.search(r"[\"'/]" + re.escape(parent) + r"[\"'/]", code):
            by_folder += 1
            continue
        rows.append((p.stat().st_size, str(rel)))
    print(f"  {len(csvs)} CSVs checked; {by_folder} are named only through their folder; {len(rows)} are named nowhere in scripts/")
    show(sorted(rows, key=lambda r: r[1]), lambda r: f"{r[0] / 1024:8.0f} KB  {r[1]}")


def check_scripts():
    print("\n== 3. Scripts no other file references ==")
    scripts = script_files()
    code = {p: read(p) for p in scripts}
    docs = {p: read(p) for p in doc_files()}
    alone, docs_only = [], []
    for p in scripts:
        if p.name in ("__init__.py", "check_repo.py"):
            continue
        stem = re.escape(p.stem)
        pat = re.compile(r"(?<![\w.])" + re.escape(p.name) + r"|(?:^|\n)\s*(?:import|from)\s+(?:scripts\.)?(?:tools\.)?" + stem + r"\b"
                         r"|import [\w, .]*\b" + stem + r"\b|from (?:scripts\.)?tools import [\w, ]*\b" + stem + r"\b")
        in_code = [q.name for q, t in code.items() if q != p and pat.search(t)]
        in_docs = [q.name for q, t in docs.items() if q.name != "README.md" and re.search(r"(?<![\w])" + re.escape(p.name), t)]
        rel = str(p.relative_to(ROOT))
        if not in_code and not in_docs:
            alone.append(rel)
        elif not in_code:
            docs_only.append((rel, in_docs))
    print(f"  {len(scripts)} scripts; {len(alone)} named by no script and no document (README inventories do not count); "
          f"{len(docs_only)} named only by a document (run by hand)")
    print("  -- named nowhere:")
    show(alone)
    print("  -- named only in documents:")
    show(docs_only, lambda r: f"{r[0]}   <- {', '.join(r[1][:3])}{' ...' if len(r[1]) > 3 else ''}")


PATH_RE = re.compile(r"(?<![\w/.\-])((?:house-hunt/)?(?:" + "|".join(PREFIXES) + r")/[A-Za-z0-9_\-./]+\.[A-Za-z0-9]{1,7})(?![\w/\-])")


def check_doc_links():
    print("\n== 4. Documents that name a file which does not exist ==")
    rows = []
    for p in doc_files():
        for n, line in enumerate(read(p).splitlines(), 1):
            for m in PATH_RE.finditer(line):
                ref = m.group(1)
                tail = line[m.end():m.end() + 1]
                if any(c in ref for c in "*<>{}") or tail in ("*", "<", "{") or "…" in ref or "..." in ref:
                    continue
                ref2 = ref[len("house-hunt/"):] if ref.startswith("house-hunt/") else ref
                ref2 = ref2.rstrip(".")
                if "<" in line[max(0, m.start() - 1):m.end() + 12] and re.search(r"<\w+>", line[m.start():m.end() + 12]):
                    continue
                if not (ROOT / ref2).exists():
                    rows.append((str(p.relative_to(ROOT)), n, ref2))
    seen, uniq = set(), []
    for r in rows:
        if (r[0], r[2]) not in seen:
            seen.add((r[0], r[2]))
            uniq.append(r)
    print(f"  {len(uniq)} missing references in {len({r[0] for r in uniq})} documents (first line of each shown)")
    show(uniq, lambda r: f"{r[0]}:{r[1]}  ->  {r[2]}")


def walk_text_files(include_raw=False):
    skip_dirs = {".git", "__pycache__", "node_modules"}
    for dirpath, dirs, names in os.walk(ROOT):
        rel = Path(dirpath).relative_to(ROOT)
        dirs[:] = [d for d in dirs if d not in skip_dirs and not (not include_raw and rel == Path(".") and d == "raw")]
        for n in names:
            p = Path(dirpath) / n
            if p.suffix.lower() in TEXT_EXT:
                yield p


def check_secrets(include_raw):
    print("\n== 5. Strings that look like an API key or token (outside raw/; values are never printed) ==")
    key_value = None
    kf = Path(os.environ.get("HOUSE_HUNT_CENSUS_KEY_FILE", "/root/.config/house-hunt/census_api_key"))
    try:
        key_value = kf.read_text().strip() or None
    except OSError:
        pass
    print(f"  local Census key file: {'present, its exact value is searched for' if key_value else 'not present here, exact-value search skipped'}")
    hits, exact = {}, []
    n_files = 0
    for p in walk_text_files(include_raw):
        rel = str(p.relative_to(ROOT))
        in_raw = rel.startswith("raw/")
        n_files += 1
        try:
            fh = open(p, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for n, line in enumerate(fh, 1):
                if key_value and key_value in line:
                    exact.append((rel, n))
                if in_raw:
                    continue        # under raw/ only the exact key is looked for: third-party pages are full of their own tokens
                if not MAYBE.search(line):
                    continue
                for kind, pat in SECRET_PATTERNS:
                    m = pat.search(line)
                    if m and not NOT_A_SECRET.search(line[max(0, m.start() - 5):m.end() + 5]):
                        hits.setdefault((rel, kind), []).append(n)
    print(f"  {n_files} text files read")
    print("  -- the exact local Census key:")
    show(exact, lambda r: f"{r[0]}:{r[1]}")
    print("  -- pattern matches (file: kind: line numbers; most are a third-party site's own public key inside a stored URL):")
    rows = sorted(hits.items())
    show(rows, lambda r: f"{r[0][0]}: {r[0][1]}: lines {', '.join(map(str, r[1][:8]))}{' ... (' + str(len(r[1])) + ' lines)' if len(r[1]) > 8 else ''}")


def main():
    global MAX
    args = sys.argv[1:]
    if "--max" in args:
        MAX = int(args[args.index("--max") + 1])
    files = tracked()
    print(f"check_repo: {ROOT}")
    print(f"tracked files under this folder: {len(files)}; on disk {sum((ROOT / f).stat().st_size for f in files if (ROOT / f).is_file()) / 1e6:.0f} MB")
    check_big(files)
    check_csvs()
    check_scripts()
    check_doc_links()
    check_secrets("--include-raw" in args)


if __name__ == "__main__":
    main()
