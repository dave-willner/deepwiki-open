"""
garvis-11z.18: Jacques self-documentation arc, wiki 1 of 2 — the core-hooks portal system (147 hooks,
the fleet's least-legible load-bearing code). Thin per-target config over the shared engine
(generate_wiki.py, genericized from generate_cope_tools_wiki.py) — see that module for the full flow
docblock (structure-determination -> per-page generation -> wiki_cache persist+round-trip verify).

Steering: jacques-mechanics-reference.md (the hand-maintained mechanics/WHY doc) — Dave-direct,
2026-07-10: "no new steering authoring this pass, existing docs only." Inlined client-side, same
pattern as garvis-9khs (never through the server's relevant_files/get_local_files_context).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/jacques-core/core-system/core-hooks",
    "repo_description": (
        "the Jacques core-hooks portal system — ~147 Claude Code lifecycle hooks "
        "(PreToolUse/PostToolUse/SessionStart/Stop/etc.) that enforce, coach, and inject expertise "
        "into every Jacques agent session"
    ),
    "owner": "local",
    "repo": "jacques-core-hooks",
    "excluded_dirs": ["./node_modules/", "./.git/"],
    "steering_doc_path": (
        "/Users/dwillner/garvis/jacques-core/core-knowledge/core-system-knowledge/"
        "jacques-mechanics-reference.md"
    ),
    # Keyword heuristic (page titles aren't known ahead of a from-scratch run) — matched against
    # each page's title+description, case-insensitive.
    "steering_keywords": (
        "hook", "portal", "role", "registry", "lifecycle", "pretooluse", "posttooluse",
        "sessionstart", "architecture", "overview", "enforce", "coach", "expertise",
    ),
    "structure_cache_path": "/tmp/jacques-core-hooks-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/jacques-core-hooks-pages-meta.json",
    "output_cache_path": "/tmp/jacques-core-hooks-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
