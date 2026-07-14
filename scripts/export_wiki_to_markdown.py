"""
Shared exporter: turns a persisted wiki_cache (output_cache_path from generate_wiki.py) + its
pages_meta (pages_meta_path) into the established numbered-markdown wiki format
(00-index.md + NN-slug.md per page), matching the pattern already shipped in wikis/bender/,
wikis/auto-doc/, etc.

Genericized out of the ad-hoc inline export snippet used for the openwiki fire (garvis-3oj3,
2026-07-14) so the remaining long-tail targets don't each re-derive it by hand. Real per-page
descriptions in frontmatter (NOT the `[object Object]` stringification bug tracked separately as
garvis-11z.12.18.7 — that bug lives in an older/different export path this script does not share
and is out of scope to fix here).

Usage: python export_wiki_to_markdown.py <output_cache_path> <pages_meta_path> <output_dir>
"""
import json
import re
import sys
from datetime import date


def slugify(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def export(output_cache_path, pages_meta_path, output_dir):
    full = json.load(open(output_cache_path))
    pages_meta = json.load(open(pages_meta_path))
    desc_by_id = {p["id"]: p["description"] for p in pages_meta}

    ws = full["wiki_structure"]
    gp = full["generated_pages"]
    title = ws["title"]
    description = ws["description"]
    today = date.today().isoformat()

    ordered_ids = [p["id"] for p in pages_meta]

    index_lines = []
    for i, pid in enumerate(ordered_ids, start=1):
        page = gp[pid]
        slug = slugify(page["title"])
        fname = f"{i:02d}-{slug}.md"
        index_lines.append(f"{i}. {page['title']} — {fname}")

        page_desc = desc_by_id.get(pid, page["title"])
        frontmatter = f"---\ndescription: {page_desc} (auto-generated {today})\n---\n\n"
        with open(f"{output_dir}/{fname}", "w") as f:
            f.write(frontmatter + page["content"])

    index_content = f"---\ndescription: {description}\n---\n\n# {title}\n\n" + "\n".join(index_lines) + "\n"
    with open(f"{output_dir}/00-index.md", "w") as f:
        f.write(index_content)

    print(f"Exported {len(ordered_ids)} pages + index to {output_dir}")


if __name__ == "__main__":
    export(sys.argv[1], sys.argv[2], sys.argv[3])
