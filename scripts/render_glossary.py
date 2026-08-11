#!/usr/bin/env python3
"""Render the Markdown and HTML glossary editions from glossary.json."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "glossary.json"
README_PATH = ROOT / "README.md"
HTML_PATH = ROOT / "index.html"
LINK_RE = re.compile(r"\[\[([^]|]+)(?:\|([^]]+))?]]")


def plain(text: str) -> str:
    return LINK_RE.sub(lambda match: match.group(2) or match.group(1), text)


def linked_html(text: str) -> str:
    pieces: list[str] = []
    cursor = 0
    for match in LINK_RE.finditer(text):
        pieces.append(html.escape(text[cursor : match.start()]))
        slug = match.group(1)
        label = match.group(2) or slug
        pieces.append(f'<a href="#{html.escape(slug, quote=True)}">{html.escape(label)}</a>')
        cursor = match.end()
    pieces.append(html.escape(text[cursor:]))
    return "".join(pieces)


def label(term: str) -> str:
    return term[:1].upper() + term[1:]


def markdown_entry(entry: dict[str, str], usage_note: str) -> str:
    return f"""### {entry['term']}

**{label(entry['term'])}** ({entry.get('usage', usage_note)})

**Example statement**

> “{plain(entry['example'])}”

**Gloss**

{entry['gloss']}

**Genus and differentia**

- **Genus:** {entry['genus']}
- **Differentia:** {entry['differentia']}
"""


def html_entry(entry: dict[str, str], usage_note: str) -> str:
    searchable = " ".join(
        plain(entry[field])
        for field in ("term", "example", "gloss", "genus", "differentia")
    )
    searchable = re.sub(r"\s+", " ", searchable)
    return f"""    <section id="{html.escape(entry['slug'], quote=True)}" class="entry" data-search="{html.escape(searchable, quote=True)}">
      <h2>{html.escape(entry['term'])} <a class="anchor" href="#{html.escape(entry['slug'], quote=True)}" aria-label="Permanent link to {html.escape(entry['term'], quote=True)}">#</a></h2>
      <p class="usage-note"><strong>{html.escape(label(entry['term']))}</strong> ({html.escape(entry.get('usage', usage_note))})</p>

      <div class="field">
        <h3>Example statement</h3>
        <blockquote>“{linked_html(entry['example'])}”</blockquote>
      </div>

      <div class="field">
        <h3>Gloss</h3>
        <p>{linked_html(entry['gloss'])}</p>
      </div>

      <div class="field">
        <h3>Genus and differentia</h3>
        <ul>
          <li><strong>Genus:</strong> {linked_html(entry['genus'])}</li>
          <li><strong>Differentia:</strong> {linked_html(entry['differentia'])}</li>
        </ul>
      </div>
    </section>"""


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    before, separator, remainder = text.partition(start)
    if not separator:
        raise ValueError(f"start marker not found: {start}")
    _, separator, after = remainder.partition(end)
    if not separator:
        raise ValueError(f"end marker not found: {end}")
    return before + start + replacement + end + after


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    entries = sorted(data["entries"], key=lambda entry: entry["term"].casefold())
    slugs = [entry["slug"] for entry in entries]
    if len(slugs) != len(set(slugs)):
        raise ValueError("entry slugs must be unique")
    known_slugs = set(slugs)
    for entry in entries:
        for field in ("example", "gloss", "genus", "differentia"):
            for match in LINK_RE.finditer(entry[field]):
                if match.group(1) not in known_slugs:
                    raise ValueError(
                        f"{entry['slug']}.{field} links to unknown slug: {match.group(1)}"
                    )

    markdown = "\n\n".join(markdown_entry(entry, data["usage_note"]).rstrip() for entry in entries)
    readme = README_PATH.read_text(encoding="utf-8")
    readme = replace_between(readme, "## Terms\n\n", "\n\n## Adding a term", markdown)
    README_PATH.write_text(readme, encoding="utf-8")

    rendered_html = "\n\n".join(html_entry(entry, data["usage_note"]) for entry in entries)
    page = HTML_PATH.read_text(encoding="utf-8")
    first_entry = re.search(r"    <section id=\"[^\"]+\" class=\"entry\"", page)
    if first_entry is None:
        raise ValueError("first HTML glossary entry not found")
    no_results = page.index('    <p id="no-results"', first_entry.start())
    page = page[: first_entry.start()] + rendered_html + "\n\n" + page[no_results:]
    HTML_PATH.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
