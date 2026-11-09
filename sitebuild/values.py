"""Resolve `{{v: path.to.value | fmt}}` references against a strategy's results JSON.

This is the part that makes the site trustworthy. Every number in an article is a
reference resolved at build time, not a figure typed into prose. A reference that
does not resolve is a build failure, so a renamed metric breaks the build instead
of quietly leaving a stale number on a published page.
"""
from __future__ import annotations

import re
from typing import Any

REF = re.compile(r"\{\{\s*v:\s*([^|}]+?)\s*(?:\|\s*([a-z0-9_]+)\s*)?\}\}", re.I)


class UnresolvedValue(Exception):
    """A value reference did not resolve, or formatted badly."""


def _pct(x: float, dp: int) -> str:
    # U+2212 MINUS SIGN, matching the typography used across the articles.
    s = f"{abs(x) * 100:.{dp}f}%"
    return ("\u2212" + s) if x < 0 else s


FORMATS = {
    "pct": lambda x: _pct(x, 1),
    "pct1": lambda x: _pct(x, 1),
    "pct2": lambda x: _pct(x, 2),
    "pct0": lambda x: _pct(x, 0),
    "num": lambda x: f"{x:,.2f}",
    "num1": lambda x: f"{x:,.1f}",
    "num0": lambda x: f"{x:,.0f}",
    "money": lambda x: f"${x:,.2f}",
    "money1": lambda x: f"${x:,.1f}",
    "x": lambda x: f"{x:.2f}",
    "raw": lambda x: str(x),
}


def lookup(data: Any, path: str) -> Any:
    """Walk a dotted path. Integer-looking segments index into lists."""
    cur = data
    for part in path.split("."):
        part = part.strip()
        try:
            if isinstance(cur, list):
                cur = cur[int(part)]
            else:
                cur = cur[part]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise UnresolvedValue(f"{path!r} failed at segment {part!r}") from exc
    return cur


def render_values(text: str, data: Any, where: str = "") -> str:
    """Replace every `{{v: ... }}` in `text`. Raises on the first bad reference."""
    problems: list[str] = []

    def sub(m: re.Match) -> str:
        path, fmt = m.group(1), (m.group(2) or "raw").lower()
        try:
            value = lookup(data, path)
        except UnresolvedValue as exc:
            problems.append(str(exc))
            return m.group(0)
        if fmt not in FORMATS:
            problems.append(f"{path!r} uses unknown format {fmt!r}; known: {', '.join(sorted(FORMATS))}")
            return m.group(0)
        try:
            return FORMATS[fmt](value)
        except (TypeError, ValueError):
            problems.append(f"{path!r} is {value!r}, which format {fmt!r} cannot render")
            return m.group(0)

    out = REF.sub(sub, text)
    if problems:
        head = f"{where}: " if where else ""
        raise UnresolvedValue(head + "; ".join(problems))
    return out
