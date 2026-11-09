"""Build the Strategy Lab site from meta.yml + content.md + results JSON.

    python -m sitebuild.generate [--out site] [--strict]

Each strategy contributes three inputs and no HTML:

    strategies/<slug>/meta.yml       taxonomy, provenance, where the numbers live
    strategies/<slug>/content.md     the prose, with values as references
    strategies/<slug>/output/*.json  the results a run produced

and the generator emits the article page, the hub, the comparison table and the
feed. Numbers reach the page only by reference, so re-running a backtest updates
every page that quotes it and a renamed metric fails the build.

Content shortcodes, beyond ordinary Markdown:

    {{v: main.cagr | pct2}}              a value from this strategy's JSON
    {{fig: charts/c1.png | caption}}     a figure with an optional caption
    {{table: tables/t1.png | alt text}}  a table image (Medium strips HTML tables)
    [drawdown](gl:drawdown)              a glossary link
    :::note ... :::                      a footnote-ish aside (references, disclaimer)
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import markdown
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sitebuild.values import UnresolvedValue, lookup, render_values  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = ROOT / "strategies"
SITE_URL = "https://algostrategylab.github.io"
AUTHOR = "Abhinav Taduka"

FIG = re.compile(r"\{\{\s*fig:\s*(.*?)\s*\}\}", re.S)
TABLE = re.compile(r"\{\{\s*table:\s*(.*?)\s*\}\}", re.S)
GLOSS = re.compile(r"\[([^\]]+)\]\(gl:([a-z0-9-]+)\)", re.I)
NOTE = re.compile(r"^:::note\s*$(.*?)^:::\s*$", re.M | re.S)


class BuildError(Exception):
    pass


@dataclass
class Strategy:
    slug: str
    meta: dict
    content: str
    results: dict

    @property
    def number(self) -> int:
        return int(self.meta["number"])

    @property
    def title(self) -> str:
        return self.meta["title"]

    def headline(self, key: str):
        """A headline metric, by the path meta.yml maps it to."""
        path = self.meta.get("headline", {}).get(key)
        if path is None:
            raise BuildError(f"{self.slug}: meta.yml has no headline.{key}")
        return lookup(self.results, path)


# ---------------------------------------------------------------- loading


def load_strategy(d: Path) -> Strategy:
    meta_path, content_path = d / "meta.yml", d / "content.md"
    if not meta_path.exists():
        raise BuildError(f"{d.name}: no meta.yml")
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    for required in ("number", "title", "deck", "published", "summary_json"):
        if required not in meta:
            raise BuildError(f"{d.name}/meta.yml: missing required field {required!r}")

    results_path = d / meta["summary_json"]
    if not results_path.exists():
        raise BuildError(f"{d.name}: summary_json points at {results_path}, which does not exist. "
                         f"Run the backtest before building the site.")
    results = json.loads(results_path.read_text(encoding="utf-8"))

    content = content_path.read_text(encoding="utf-8") if content_path.exists() else ""
    return Strategy(d.name, meta, content, results)


def load_all() -> list[Strategy]:
    found = [load_strategy(d) for d in sorted(STRATEGIES.iterdir())
             if d.is_dir() and (d / "meta.yml").exists()]
    if not found:
        raise BuildError(f"no strategies with a meta.yml under {STRATEGIES}")
    numbers = [s.number for s in found]
    if len(set(numbers)) != len(numbers):
        raise BuildError(f"duplicate article numbers: {sorted(numbers)}")
    return sorted(found, key=lambda s: s.number)


# ---------------------------------------------------------------- content


def _figure(payload: str, kind: str) -> str:
    """`src | alt text | caption` — alt is for screen readers and Medium, the
    caption is the visible line under the image. They are different things, and
    collapsing them is how alt text ends up printed on the page."""
    parts = [p.strip() for p in payload.split("|")]
    src = parts[0]
    alt = parts[1] if len(parts) > 1 else ""
    caption = parts[2] if len(parts) > 2 else ""
    out = f'<figure><img src="../assets/{kind}/{src}" alt="{html.escape(alt, quote=True)}">'
    if caption:
        out += f"<figcaption>{html.escape(caption)}</figcaption>"
    return out + "</figure>"


def expand_shortcodes(text: str, s: Strategy) -> str:
    text = render_values(text, s.results, where=f"{s.slug}/content.md")
    text = FIG.sub(lambda m: _figure(m.group(1), "charts"), text)
    text = TABLE.sub(lambda m: _figure(m.group(1), "tables"), text)
    text = GLOSS.sub(lambda m: f'<a class="gl" href="../glossary/#{m.group(2)}">{m.group(1)}</a>', text)

    def note(m: re.Match) -> str:
        body = markdown.markdown(m.group(1).strip())
        body = re.sub(r"^<p>|</p>$", "", body.strip())
        return f'<p class="note">{body}</p>'

    text = NOTE.sub(note, text)
    return text


def inline(text: str, s: Strategy) -> str:
    """Expand shortcodes and inline Markdown in a short meta field.

    meta.yml holds prose too (the deck, the references, the next-up teaser), so
    `_Dual Momentum Investing_` has to become italics there as it does in the body.
    """
    out = markdown.markdown(expand_shortcodes(text, s))
    return re.sub(r"^<p>|</p>$", "", out.strip())


def render_body(s: Strategy) -> str:
    md = expand_shortcodes(s.content, s)
    return markdown.markdown(md, extensions=["extra", "sane_lists"])


# ---------------------------------------------------------------- pages


def page_shell(title: str, description: str, canonical: str, og_image: str,
               body: str, depth: int = 1) -> str:
    up = "../" * depth
    esc = html.escape
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description, quote=True)}">
<meta name="author" content="{AUTHOR}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title, quote=True)}">
<meta property="og:description" content="{esc(description, quote=True)}">
<meta property="og:image" content="{og_image}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="Strategy Lab" href="{SITE_URL}/feed.xml">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="{up}">Strategy Lab</a>
  <nav><a href="{up}">All strategies</a><a href="{up}glossary/">Glossary</a><a href="https://github.com/AlgoStrategyLab/strategy-lab">GitHub</a><a href="{up}feed.xml">RSS</a></nav>
</div></header>

<div class="wrap">
{body}
</div>

<footer class="site"><div class="wrap">
Strategy Lab &middot; <a href="https://github.com/AlgoStrategyLab/strategy-lab">github.com/AlgoStrategyLab</a> &middot; <a href="{up}feed.xml">RSS</a>
</div></footer>
</body>
</html>
"""


def code_paragraph(s: Strategy) -> str:
    """The Code/Engine line, identical in every article by construction.

    It is a <p> and not a <ul> on purpose: Medium's importer silently drops list
    elements, which is how articles #1-#3 each lost their repo links after import.
    """
    repo = s.meta.get("repo", "strategy-lab")
    path = f"https://github.com/AlgoStrategyLab/strategy-lab/tree/main/strategies/{s.slug}"
    return (f'<p><strong>Code:</strong> <a href="{path}">strategy-lab/strategies/{s.slug}</a>'
            f' &mdash; this strategy, with every output file committed.'
            f' <strong>Engine:</strong> <a href="https://github.com/AlgoStrategyLab/strategy-lab">'
            f'AlgoStrategyLab/strategy-lab</a> &mdash; the shared harness, MIT licensed.</p>')


def human_date(value) -> str:
    """'2026-10-22' -> '22 October 2026', matching the byline the articles already use."""
    d = value if hasattr(value, "strftime") else datetime.fromisoformat(str(value)).date()
    return f"{d.day} {d.strftime('%B %Y')}"


def article_page(s: Strategy, nxt: Strategy | None) -> str:
    published = human_date(s.meta["published"])
    body = [
        "<article>",
        f"<h1>{html.escape(s.title)}</h1>",
        f'<p class="deck">{inline(s.meta["deck"], s)}</p>',
        f'<p class="byline">{AUTHOR} &middot; {published} &middot; Strategy Lab #{s.number}</p>',
        render_body(s),
        "<h2>The code</h2>",
        f"<p>{inline(s.meta.get('code_note', 'Everything here runs on the same open-source harness as the rest of the series.'), s)}</p>",
        f"<pre><code>pip install -r requirements.txt\npython strategies/{s.slug}/run.py\npython strategies/{s.slug}/make_charts.py</code></pre>",
        code_paragraph(s),
    ]
    if s.meta.get("code_footer"):
        body.append(f"<p>{inline(s.meta['code_footer'], s)}</p>")
    teaser = s.meta.get("next_teaser") or (nxt.title if nxt else None)
    if teaser:
        body.append(f'<p><strong>Next up:</strong> {inline(teaser, s)}</p>')
    body.append("<hr>")
    if s.meta.get("references"):
        body.append(f'<p class="note"><strong>References.</strong> {inline(s.meta["references"], s)}</p>')
    body.append('<p class="note">This is research and education, not investment advice. '
                "Backtests benefit from hindsight in instrument choice and start date, "
                "and past performance does not predict future results.</p>")
    body.append("</article>")

    og = s.meta.get("og_image", "")
    og_url = f"{SITE_URL}/assets/charts/{og}" if og else f"{SITE_URL}/assets/charts/"
    return page_shell(s.title, s.meta.get("og_description", s.meta["deck"]),
                      f"{SITE_URL}/{s.slug}/", og_url, "\n".join(body), depth=1)


def hub_page(strategies: list[Strategy]) -> str:
    cards = []
    for s in reversed(strategies):
        cards.append(
            f'<li class="card">'
            f'<a href="{s.slug}/"><h3>{html.escape(s.title)}</h3></a>'
            f'<p class="deck">{inline(s.meta["deck"], s)}</p>'
            f'<p class="meta">Strategy Lab #{s.number} &middot; {human_date(s.meta["published"])} &middot; '
            f'{html.escape(str(s.meta.get("family", "")))}</p>'
            f'</li>'
        )
    body = ("<article>\n<h1>Strategy Lab</h1>\n"
            '<p class="deck">Systematic trading strategies backtested properly: exact rules, '
            "every metric, the robustness tests that decide whether any of it means anything, "
            "and all the code.</p>\n"
            f'<p><a href="compare/">Compare every strategy side by side &rarr;</a></p>\n'
            f'<ul class="cards">\n' + "\n".join(cards) + "\n</ul>\n</article>")
    return page_shell("Strategy Lab — backtested systematic strategies",
                      "Systematic trading strategies backtested with full robustness testing and open code.",
                      f"{SITE_URL}/", f"{SITE_URL}/assets/charts/", body, depth=0)


def compare_page(strategies: list[Strategy]) -> str:
    """The view a per-strategy repo layout cannot produce: every result, one table,
    all generated by one engine at one version."""
    rows = []
    for s in strategies:
        def fmt(key, pct=True):
            try:
                v = s.headline(key)
            except (BuildError, UnresolvedValue):
                return "&mdash;"
            return f"{v * 100:.2f}%".replace("-", "−") if pct else f"{v:.2f}"
        rows.append(
            f"<tr><td><a href=\"../{s.slug}/\">{html.escape(s.title.split('.')[0])}</a></td>"
            f"<td>{html.escape(str(s.meta.get('family','')))}</td>"
            f"<td>{html.escape(str(s.meta.get('frequency','')))}</td>"
            f"<td>{fmt('cagr')}</td><td>{fmt('sharpe', pct=False)}</td>"
            f"<td>{fmt('max_drawdown')}</td></tr>"
        )
    body = ("<article>\n<h1>Every strategy, side by side</h1>\n"
            '<p class="deck">One engine, one execution model, one cost assumption. '
            "Numbers come straight from each run's JSON, so this table cannot drift "
            "from the articles that quote it.</p>\n"
            "<table class=\"compare\">\n<thead><tr><th>Strategy</th><th>Family</th><th>Rebalance</th>"
            "<th>CAGR</th><th>Sharpe</th><th>Max DD</th></tr></thead>\n<tbody>\n"
            + "\n".join(rows) + "\n</tbody>\n</table>\n</article>")
    return page_shell("Compare every Strategy Lab backtest",
                      "Every backtested strategy side by side, generated from the same engine and the same results files.",
                      f"{SITE_URL}/compare/", f"{SITE_URL}/assets/charts/", body, depth=1)


def feed_xml(strategies: list[Strategy]) -> str:
    items = []
    for s in reversed(strategies):
        pub = datetime.fromisoformat(str(s.meta["published"])).replace(tzinfo=timezone.utc)
        items.append(
            "<item>\n"
            f"<title>{html.escape(s.title)}</title>\n"
            f"<link>{SITE_URL}/{s.slug}/</link>\n"
            f"<guid isPermaLink=\"true\">{SITE_URL}/{s.slug}/</guid>\n"
            f"<pubDate>{format_datetime(pub)}</pubDate>\n"
            f"<description>{html.escape(s.meta.get('og_description', s.meta['deck']))}</description>\n"
            "</item>"
        )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0"><channel>\n'
            "<title>Strategy Lab</title>\n"
            f"<link>{SITE_URL}/</link>\n"
            "<description>Systematic trading strategies, backtested properly.</description>\n"
            "<language>en</language>\n" + "\n".join(items) + "\n</channel></rss>\n")


# ---------------------------------------------------------------- build


def build(out: Path) -> list[str]:
    strategies = load_all()
    out.mkdir(parents=True, exist_ok=True)
    written = []

    for i, s in enumerate(strategies):
        nxt = strategies[i + 1] if i + 1 < len(strategies) else None
        d = out / s.slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(article_page(s, nxt), encoding="utf-8")
        written.append(f"{s.slug}/index.html")

        for kind, sub in (("charts", "charts"), ("tables", "tables")):
            srcdir = STRATEGIES / s.slug / ("output" if kind == "charts" else "tables")
            if not srcdir.exists():
                continue
            dest = out / "assets" / sub
            dest.mkdir(parents=True, exist_ok=True)
            for png in srcdir.glob("*.png"):
                shutil.copy2(png, dest / png.name)

    (out / "index.html").write_text(hub_page(strategies), encoding="utf-8")
    (out / "compare").mkdir(parents=True, exist_ok=True)
    (out / "compare" / "index.html").write_text(compare_page(strategies), encoding="utf-8")
    (out / "feed.xml").write_text(feed_xml(strategies), encoding="utf-8")
    written += ["index.html", "compare/index.html", "feed.xml"]
    if update_readme(strategies):
        written.append("../README.md")
    return written


README_START = "<!-- strategies:start -->"
README_END = "<!-- strategies:end -->"


def readme_table(strategies: list[Strategy]) -> str:
    """The repo README's strategy table, generated for the same reason the pages are."""
    rows = ["| # | Strategy | Family | Rebalance | Period | CAGR | Sharpe | Max DD |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in strategies:
        per = s.meta.get("period", {})
        years = f"{str(per.get('start', ''))[:4]}–{str(per.get('end', ''))[:4]}"
        def f(key, pct=True):
            try:
                v = s.headline(key)
            except (BuildError, UnresolvedValue):
                return "—"
            return f"{v * 100:.2f}%".replace("-", "\u2212") if pct else f"{v:.2f}"
        rows.append(
            f"| {s.number:02d} | [{s.title.split('.')[0]}](strategies/{s.slug}) "
            f"| {s.meta.get('family','')} | {s.meta.get('frequency','')} | {years} "
            f"| {f('cagr')} | {f('sharpe', pct=False)} | {f('max_drawdown')} |")
    return "\n".join(rows)


def update_readme(strategies: list[Strategy]) -> bool:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    if README_START not in text or README_END not in text:
        return False
    head, rest = text.split(README_START, 1)
    _, tail = rest.split(README_END, 1)
    path.write_text(f"{head}{README_START}\n{readme_table(strategies)}\n{README_END}{tail}",
                    encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "site"), help="output directory")
    args = ap.parse_args()
    try:
        written = build(Path(args.out))
    except (BuildError, UnresolvedValue) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    print(f"built {len(written)} files into {args.out}")
    for w in written:
        print("  ", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
