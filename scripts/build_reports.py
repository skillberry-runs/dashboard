#!/usr/bin/env python3
"""Render a skillberry-runs results repo (parsec, spreadsheetbench, ...) onto the dashboard site.

    python3 scripts/build_reports.py --src <checkout> --out site/<bench> \
        --repo skillberry-runs/<bench> --title "<Display name>"

What gets published (and what doesn't) is a deliberate policy, agreed when these repos
were made public on the dashboard (2026-11-10):

- PUBLISHED: every *.md write-up (rendered to HTML in the site chrome) and every
  standalone *.html report page (copied, with links rewritten), outside UNPUBLISHED_TOP.
- NOT PUBLISHED: raw results data (*.json, *.jsonl, logs, ...), and everything under
  UNPUBLISHED_TOP (recipes/ and artifacts/ embed internal cluster paths; presentations/
  are slide decks with their own JS bundles). Links to those go to the source repo on
  GitHub instead, marked as external.
- MASKED: internal cluster paths and host names in published text (see REDACTIONS).
  The source repos are untouched; only the published copy is masked.

The README becomes the section's index page, with a "Report pages" list of the
standalone HTML reports added on top.
"""
from __future__ import annotations

import argparse
import html as html_lib
import posixpath
import re
import shutil
import sys
from pathlib import Path

import markdown as md_lib

UNPUBLISHED_TOP = {".git", ".github", "artifacts", "recipes", "presentations"}
SKIP_FILES = {".gitignore"}
MD_EXTENSIONS = ["tables", "fenced_code", "toc", "attr_list", "sane_lists"]
CAP_EVOLVE_SITE = "https://skillberry-ai.github.io/cap-evolve"

# (pattern, replacement) applied to published text. Order matters: paths before hosts.
REDACTIONS = [
    (re.compile(r"/(?:dccstor|proj|u)/[^\s`'\"<>)\]|,;]*"), "<internal path>"),
    (re.compile(r"\bccc[a-z]{1,3}\d{2,4}(?:\.[a-z0-9.-]+)?\b"), "<cluster host>"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[a-z.]*ibm\.com\b"), "<email>"),
]


def redact(text: str) -> tuple[str, int]:
    n = 0
    for pat, rep in REDACTIONS:
        text, k = pat.subn(rep, text)
        n += k
    return text, n


def is_published(rel: str) -> bool:
    parts = rel.split("/")
    if parts[0] in UNPUBLISHED_TOP or parts[-1] in SKIP_FILES:
        return False
    return rel.endswith((".md", ".html"))


class Builder:
    def __init__(self, src: Path, out: Path, repo: str, title: str, ref: str = "main"):
        self.src, self.out, self.repo, self.title, self.ref = src, out, repo, title, ref
        self.n_redacted = 0
        self.src_prefix = ""

    # ---- links -------------------------------------------------------------
    def gh_url(self, rel: str) -> str:
        kind = "tree" if (self.src / rel).is_dir() or rel.endswith("/") else "blob"
        path = posixpath.join(self.src_prefix, rel.rstrip("/")) if self.src_prefix else rel.rstrip("/")
        return f"https://github.com/{self.repo}/{kind}/{self.ref}/{path}"

    def map_target(self, cur_dir: str, path: str) -> str | None:
        """Site-relative replacement for a relative link, or None to leave it alone."""
        resolved = posixpath.normpath(posixpath.join(cur_dir, path))
        if resolved.startswith("../") or resolved == "..":
            return None  # points outside the repo; leave as-is
        if resolved == "README.md":  # the README is rendered as the section's index page
            return posixpath.relpath("index.html", cur_dir or ".")
        if is_published(resolved):
            return path[: -len(".md")] + ".html" if path.endswith(".md") else path
        if (self.src / resolved).exists():
            return self.gh_url(resolved + ("/" if path.endswith("/") else ""))
        return None

    def rewrite_links(self, text: str, cur_dir: str) -> str:
        def href(m: re.Match) -> str:
            attr, q, url = m.group(1), m.group(2), m.group(3)
            if re.match(r"^([a-z][a-z0-9+.-]*:|#|\$\{)", url):
                return m.group(0)
            path, sep, frag = url.partition("#")
            if not path:
                return m.group(0)
            new = self.map_target(cur_dir, path)
            if new is None:
                return m.group(0)
            ext = ' class="ext-link"' if new.startswith("https://") and attr == "href" else ""
            return f"{attr}={q}{new}{sep}{frag}{q}{ext}"

        text = re.sub(r'\b(href|src)=(["\'])([^"\']+?)\2', href, text)

        # Report pages build links from embedded data, e.g. {"report": "reports/v1/x.md"}
        # rendered as href="../${r.report}". Rewrite such .md string literals too, when
        # they name a published file (resolved relative to the repo root or this page).
        def literal(m: re.Match) -> str:
            q, path = m.group(1), m.group(2)
            for base in ("", cur_dir):
                resolved = posixpath.normpath(posixpath.join(base, path))
                if resolved == "README.md":
                    return f"{q}{posixpath.relpath('index.html', base or '.')}{q}"
                if is_published(resolved) and (self.src / resolved).is_file():
                    return f"{q}{path[:-3]}.html{q}"
            return m.group(0)

        return re.sub(r'(["\'])((?:\.\./)*[A-Za-z0-9_./-]+\.md)\1', literal, text)

    # ---- chrome ------------------------------------------------------------
    def chrome(self, title: str, body: str, rel_out: str, source_rel: str | None) -> str:
        depth = rel_out.count("/")
        site = "/".join([".."] * (depth + 1))  # dashboard site root
        hub = "/".join([".."] * depth) or "."
        src_link = (
            f'<a class="ext-link" href="{self.gh_url(source_rel)}">source</a>'
            if source_rel else ""
        )
        t = html_lib.escape(title)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{t} — {html_lib.escape(self.title)}</title>
  <link rel="icon" href="{site}/assets/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Fira+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <script>(function(){{try{{document.documentElement.setAttribute('data-theme',localStorage.getItem('capevolve-theme')||'dark');}}catch(e){{document.documentElement.setAttribute('data-theme','dark');}}document.documentElement.classList.add('js');}})();</script>
  <link rel="stylesheet" href="{site}/style.css?v=20260908a">
</head>
<body>
<nav class="nav">
  <div class="nav-inner">
    <a class="nav-brand" href="{CAP_EVOLVE_SITE}/"><img src="{site}/assets/logo-300.png" alt="" class="nav-brand-logo" aria-hidden="true"><span class="wordmark">cap<span class="wordmark-dot">·</span>evolve</span></a>
    <div class="nav-links" id="nav-links">
      <a href="{site}/">Benchmark runs</a>
      <a href="{site}/parsec/">Parsec</a>
      <a href="{site}/spreadsheetbench/">SpreadsheetBench</a>
      <a href="{CAP_EVOLVE_SITE}/skillsbench/">SkillsBench</a>
      <a class="gh" href="https://github.com/{self.repo}">GitHub</a>
    </div>
  </div>
</nav>
<main class="page-narrow doc">
  <p class="muted" style="font-size:0.9rem;margin-bottom:1.2rem;">
    <a href="{hub}/index.html">{html_lib.escape(self.title)}</a> · {html_lib.escape(source_rel or rel_out)} {src_link}
  </p>
{body}
</main>
<script src="{site}/js/site.js?v=20260822" defer></script>
</body>
</html>
"""

    # ---- build -------------------------------------------------------------
    def render_md(self, rel: str) -> None:
        text, n = redact((self.src / rel).read_text(encoding="utf-8"))
        self.n_redacted += n
        body = md_lib.markdown(text, extensions=MD_EXTENSIONS)
        body = self.rewrite_links(body, posixpath.dirname(rel))
        out_rel = "index.html" if rel == "README.md" else rel[:-3] + ".html"
        if rel == "README.md":
            body = self.report_list() + body
        title = rel.rsplit("/", 1)[-1][:-3]
        page = self.chrome(self.title if rel == "README.md" else title, body, out_rel, rel)
        self.write(out_rel, page)

    def copy_html(self, rel: str) -> None:
        text, n = redact((self.src / rel).read_text(encoding="utf-8"))
        self.n_redacted += n
        self.write(rel, self.rewrite_links(text, posixpath.dirname(rel)))

    def report_list(self) -> str:
        pages = sorted(p for p in self.published if p.endswith(".html"))
        if not pages:
            return ""
        items = []
        for rel in pages:
            m = re.search(r"<title>(.*?)</title>", (self.src / rel).read_text(encoding="utf-8"), re.S)
            label = html_lib.escape(m.group(1).strip()) if m else rel
            items.append(f'<li><a href="{rel}">{label}</a> <span class="muted">({rel})</span></li>')
        return (
            '<div class="callout callout-accent"><p class="callout-title">Report pages</p>'
            f'<ul>{"".join(items)}</ul>'
            "<p class=\"muted\" style=\"font-size:0.88rem\">Raw results data, recipes, artifacts and "
            "presentations are not published here; links to them go to the source repo on GitHub "
            "(team access). Internal cluster paths and host names are masked on this site.</p></div>\n"
        )

    def write(self, rel_out: str, text: str) -> None:
        p = self.out / rel_out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def build(self) -> dict:
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        self.published = sorted(
            p.relative_to(self.src).as_posix()
            for p in self.src.rglob("*")
            if p.is_file() and is_published(p.relative_to(self.src).as_posix())
        )
        n_md = n_html = 0
        for rel in self.published:
            if rel.endswith(".md"):
                self.render_md(rel)
                n_md += 1
            else:
                self.copy_html(rel)
                n_html += 1
        if not (self.out / "index.html").exists():
            self.write("index.html", self.chrome(self.title, self.report_list(), "index.html", None))
        return {"md": n_md, "html": n_html, "redactions": self.n_redacted}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, type=Path, help="checkout of the results repo")
    ap.add_argument("--out", required=True, type=Path, help="output dir, e.g. site/parsec")
    ap.add_argument("--repo", required=True, help="GitHub repo for source links, e.g. skillberry-runs/parsec")
    ap.add_argument("--title", required=True, help="display name, e.g. Parsec")
    ap.add_argument("--ref", default="main")
    ap.add_argument("--src-prefix", default="", help="path of --src inside --repo (for source links)")
    a = ap.parse_args()
    b = Builder(a.src, a.out, a.repo, a.title, a.ref)
    b.src_prefix = a.src_prefix.strip("/")
    stats = b.build()
    print(f"{a.title}: rendered {stats['md']} .md, copied {stats['html']} .html, masked {stats['redactions']} internal paths/hosts")
    return 0 if (a.out / "index.html").exists() else 1


if __name__ == "__main__":
    sys.exit(main())
