"""
garvis-gj8z: the auto-doc wiki — the articulate->audit trust engine (our OWN tool: an LLM voice drafts
how a system works, the trust engine verifies every checkable claim before it renders as fact). Pre-req
context for the ekve auditor-as-lint integration. Standard repo-walk mode over
/Users/dwillner/garvis/projects/auto-doc. Thin per-target config over the shared engine
(generate_wiki.py) — see that module for the full flow docblock.

STEERING DOC: README.md (38KB) — chosen because it carries the LOAD-BEARING epistemic-status banner
("Status: GRADUATED... TRUE-100%... Honest scope — this is NOT a bare 100%...") plus the full
mutation-testing graduation tallies and the documented-equivalents discipline. This status framing is
exactly what the wiki must NOT flatten into an unqualified "it's tested" claim — the lead's explicit
instruction: keep the ungraduated/graduated honesty labels surfacing, they're load-bearing epistemic
status, not decoration. auto-doc.md (the vault folder-note, mission + 8-module architecture) is smaller
and stays in-corpus as an ordinary citable file rather than the primary steering doc, since README.md is
the one carrying the graduation/honesty banner itself.

NEW HARDENING USED HERE (garvis-gj8z gate finding, generate_wiki.py): this repo has a top-level
`mutation.json` data file that is 107MB — harmless as a single file_tree listing line (structure-
determination never reads file contents besides the README) but would be catastrophic if the model
ever picked it as a `relevant_file` for a page (the server would try to read the whole thing into a
prompt). Added `disallowed_relevant_files` to the shared engine: a client-side filter, applied right
after structure-determination and before any page-generation call, that strips matching basenames from
every page's filePaths — logged, never silent. Optional and defaults to empty, so every prior target's
behavior is unchanged.

Account: fresh courtesy invariant-9 sweep run immediately before firing; server already pinned
DEEPWIKI_CLAUDE_ACCOUNT_DIR=/Users/dwillner/.claude-overflow-3 (claude-max-03@zentropi.ai). No git
commit this run — the box's git is fleet-wide P0-blocked (Xcode license re-lock); output is written to
disk only and will be committed in the batched catch-up pass once git returns.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/auto-doc",
    "repo_description": (
        "auto-doc — the articulate-then-audit trust engine for self-documenting Jacques systems: a "
        "constrained LLM voice articulates how a system works, then every checkable claim is audited "
        "against running code (behavioral claims via a hermetic sandbox + test-output verification, "
        "structural claims via static code-graph checks) before it renders as fact. Unverified or "
        "false claims are held out of the body and flagged, never laundered into the document. The 7 "
        "pure-core correctness modules (writeup-core, system-writeup-core, frame-extractor-core, "
        "trail-extractor-core, verifier-core, articulate-audit-core, system-articulate-audit-core) "
        "are stryker TRUE-100%-graduated; the I/O wrappers around them are behaviorally gated by "
        "integration suites instead, out of mutation scope by design."
    ),
    "owner": "local",
    "repo": "auto-doc",
    "excluded_dirs": ["./node_modules/", "./.git/"],
    "disallowed_relevant_files": ["mutation.json"],
    "steering_doc_path": "/Users/dwillner/garvis/projects/auto-doc/README.md",
    "steering_keywords": (
        "architecture", "overview", "pipeline", "articulate", "audit", "verify", "trail", "frame",
        "sandbox", "writeup", "mutation", "graduat", "stryker", "trust", "claim", "equivalent",
        "status", "honest",
    ),
    "structure_cache_path": "/tmp/auto-doc-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/auto-doc-pages-meta.json",
    "output_cache_path": "/tmp/auto-doc-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
