"""
garvis-11z.19: Jacques self-documentation arc, wiki 2 of 2 — the core machinery (core-system with
core-hooks EXCLUDED, since wiki 1 covers that separately): core-scripts (incl. the jacques launcher),
core-mcp servers (thread/spindle/phone/beads), core-settings, core-templates, core-agents,
core-commands. Thin per-target config over the shared engine (generate_wiki.py) — see that module for
the full flow docblock.

Steering: same jacques-mechanics-reference.md as wiki 1 (existing doc, no new authoring this pass).

excluded_dirs carries core-hooks (this wiki's own scope boundary) plus node_modules (5 instances
across the core-mcp/* server subprojects, all excluded by one token match since exclusion-mode
matching is per-path-component, not a single fixed depth).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/jacques-core/core-system",
    "repo_description": (
        "the Jacques core-system machinery (core-hooks is a SEPARATE, already-documented wiki and "
        "is excluded from this tree) — the jacques launcher + core-scripts, the core-mcp servers "
        "(thread-management, spindle-management, phone-system-mcp, beads-mcp, obsidian-cli-mcp), "
        "core-settings, core-templates, core-agents, and core-commands"
    ),
    "owner": "local",
    "repo": "jacques-core-system",
    "excluded_dirs": ["./core-hooks/", "./node_modules/", "./.git/"],
    "steering_doc_path": (
        "/Users/dwillner/garvis/jacques-core/core-knowledge/core-system-knowledge/"
        "jacques-mechanics-reference.md"
    ),
    "steering_keywords": (
        "launcher", "mcp", "spindle", "thread", "phone", "beads", "settings", "template",
        "agent", "command", "architecture", "overview", "lifecycle",
    ),
    "structure_cache_path": "/tmp/jacques-core-system-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/jacques-core-system-pages-meta.json",
    "output_cache_path": "/tmp/jacques-core-system-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
