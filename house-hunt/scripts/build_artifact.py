"""Turn the built page into the file that is published as an artifact: site/dist/index.html -> site/dist/artifact.html.

The publishing host wraps the file in its own document, so the page's outer shell is taken off and everything else is
kept byte for byte:

  removed   <!DOCTYPE ...>, <html ...>, <head>, </head>, <body ...>, </body>, </html>,
            <meta charset=...> and <meta name="viewport" ...>
  kept      <title>, every other <meta> and <link>, the styles, and all of the body (markup, scripts, inlined data)

Only the OUTER tags are touched: the head is everything before the first </head>, the body opens at the first <body>
after it, and the closing tags are looked for at the very end of the file. The page's scripts and the six megabytes of
inlined data are never searched, so a "<body>" inside a string stays as it is.

  python3 scripts/build_artifact.py                       site/dist/index.html -> site/dist/artifact.html
  python3 scripts/build_artifact.py --banner "Preview, Nov 16. The list is still being checked."
  python3 scripts/build_artifact.py --src A.html --out B.html

--banner puts one line right at the start of the body, styled with the page's own CSS variables (--butter, --ink,
--body). The result must have its <title> inside the first 8 KB and be under 16 MB; the size is printed. Exit code 1
when a check fails (the file is still written, so it can be looked at) or the source is not a whole page. Idempotent.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "site" / "dist"
TITLE_WITHIN = 8 * 1024
MAX_BYTES = 16 * 1024 * 1024
BANNER_STYLE = ("background:var(--butter);color:var(--ink);font:600 13px/1.3 var(--body);"
                "padding:8px max(16px, env(safe-area-inset-right, 0px)) 8px max(16px, env(safe-area-inset-left, 0px))")

_LINE_END = r"[ \t]*\r?\n?"
HEAD_ONLY = [re.compile(p + _LINE_END, re.I) for p in (
    r"<!DOCTYPE[^>]*>", r"<html\b[^>]*>", r"<head\b[^>]*>",
    r"<meta\b[^>]*\bcharset\s*=[^>]*>", r"<meta\b[^>]*\bname\s*=\s*[\"']?viewport[\"']?(?=[\s>/])[^>]*>")]
HEAD_END = re.compile(r"</head\s*>" + _LINE_END, re.I)
BODY_START = re.compile(r"\s*<body\b[^>]*>" + _LINE_END + r"(?:[ \t]*\r?\n)?", re.I)
TAIL = re.compile(r"\s*</body\s*>\s*(?:</html\s*>)?\s*$|\s*</html\s*>\s*$", re.I)


def banner_html(text: str) -> str:
    return f'<div id="draftbar" role="note" style="{BANNER_STYLE}">{html.escape(text, quote=False)}</div>\n'


def to_artifact(page: str, banner: str | None = None) -> str:
    """The page without its outer shell (see the module text). Raises ValueError when the page has no </head> or no
    <body> after it."""
    m = HEAD_END.search(page)
    if not m:
        raise ValueError("no </head> in the page")
    head, rest = page[:m.start()], page[m.end():]
    for rx in HEAD_ONLY:
        head = rx.sub("", head)
    b = BODY_START.match(rest)
    if not b:
        raise ValueError("no <body> right after </head>")
    body = TAIL.sub("", rest[b.end():])
    return head + (banner_html(banner) if banner else "") + body + "\n"


def check(text: str) -> list[str]:
    """What is wrong with an artifact file, as sentences (empty when it is fine)."""
    raw = text.encode("utf-8")
    out = []
    if not re.search(rb"<title\b[^>]*>[^<]*\S[^<]*</title>", raw[:TITLE_WITHIN], re.I):
        out.append(f"no <title> in the first {TITLE_WITHIN // 1024} KB")
    if len(raw) >= MAX_BYTES:
        out.append(f"{len(raw):,} bytes: not under {MAX_BYTES // (1024 * 1024)} MB")
    for tag in ("<!doctype", "<html", "<head", "</head", "<meta charset"):
        if tag in text[:TITLE_WITHIN].lower():
            out.append(f"{tag}...> is still in the head")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="site/dist/index.html -> site/dist/artifact.html (the page without its outer shell).")
    ap.add_argument("--src", default=str(DIST / "index.html"))
    ap.add_argument("--out", default=str(DIST / "artifact.html"))
    ap.add_argument("--banner", default=None, help="one line shown at the very top of the page")
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    try:
        page = src.read_text(encoding="utf-8")
        text = to_artifact(page, a.banner)
    except (OSError, ValueError) as e:
        print(f"build_artifact: {src}: {e}; nothing written")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    size = len(text.encode("utf-8"))
    problems = check(text)
    print(f"{out}: {size:,} bytes ({size / (1024 * 1024):.2f} MB of {MAX_BYTES // (1024 * 1024)} MB)" + (", with a banner" if a.banner else ""))
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
