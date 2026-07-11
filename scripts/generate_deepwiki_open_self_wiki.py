"""
garvis-ownx: the deepwiki-open self-wiki — the engine documenting itself. Standard repo-walk mode over
this very repo, /Users/dwillner/garvis/projects/deepwiki-open. Thin per-target config over the shared
engine (generate_wiki.py) — this run is genuinely self-referential (the engine generating a wiki about
itself, using itself).

SELF-REFERENTIAL-GREP WARNING APPLIES MAXIMALLY HERE (per the lead's explicit note): this repo IS the
tripwire/guard code. `api/claude_code_client.py`'s own source contains the literal isolation-failure log
message string — if that file is (correctly) selected as a relevant_file for an architecture page, the
GENERATED WIKI TEXT may legitimately quote it. That is expected and fine for the wiki content. The
actual gate check is scoped to the SERVER's application.log, not the generated content, and further
scoped to the structured log-line FORMAT a real trigger emits (`- ERROR - api.claude_code_client -
claude_code_client.py:`) rather than a bare substring match — a bare match could theoretically also fire
on some OTHER logger dumping raw prompt/file content that happens to embed this file's own source as
context (the exact poisoning class seen once already this arc, on an unrelated ollama-embedding log
line).

STEERING DOC: no single existing doc owns the fork's own story — upstream's README.md is a 2KB generic
stub, unaware it's been forked. Self-authored a purpose-written steering doc (same pattern as the
Distaff wiki's distaff-wiki-steering.md), grounded in this fork's REAL commit history (shas verified via
`git log`, not reconstructed): the account-pin design, a tool-availability-vs-permission security fix
(5b4a7ca), the retrieval-starvation fix (cd389c7), the exclusion-token fixes (bf83691, 01fac5b/
garvis-11z.17), this session's two hardenings (an XML entity-sanitization fix + a huge-file
relevant_files guard, 1dc230e/2b172ad), manifest-corpus mode, and the genericized shared-engine design
(518647c).

Exclusions: api/logs/ (37MB, real application logs, not documentation), corpus/ (my own Distaff staging
dir, transient scratch, not part of THIS repo's own architecture), .pytest_cache/, api/__pycache__/,
.git/. node_modules/ and .venv/ kept in the exclusion list for parity/future-proofing even though
neither currently exists in this checkout (the JS frontend's deps + the Python API's venv both live
outside this repo's own tree right now — package.json/yarn.lock/uv.lock are present but uninstalled).

Account: fresh courtesy invariant-9 sweep run immediately before firing; server already pinned
DEEPWIKI_CLAUDE_ACCOUNT_DIR=/Users/dwillner/.claude-overflow-3 (claude-max-03@zentropi.ai). Git commit
via the sanctioned DEVELOPER_DIR=/Library/Developer/CommandLineTools interim prefix, driver + export
committed together.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/deepwiki-open",
    "repo_description": (
        "deepwiki-open — a fork of AsyncFuncAI/deepwiki-open re-pointed at the Claude Agent SDK on a "
        "Max subscription (never a metered API key, never a third-party proxy; code never leaves the "
        "machine) via a custom ClaudeCodeClient ModelClient provider, plus a genericized shared "
        "wiki-generation engine (generate_wiki.py) used by ~10 thin per-target driver configs to "
        "document Jacques' own tools and design surfaces. Carries production-earned hardenings "
        "upstream lacks: direct local-file retrieval (not FAISS starvation), server-side exclusion-dir "
        "filtering with a shared token-cleaning helper, a real tool-availability isolation fix, XML "
        "entity-sanitization, a huge-file relevant_files guard, and a manifest-corpus mode for "
        "non-contiguous curated design-surface targets."
    ),
    "owner": "local",
    "repo": "deepwiki-open",
    "excluded_dirs": [
        "./api/logs/", "./corpus/", "./.pytest_cache/", "./api/__pycache__/", "./node_modules/",
        "./.venv/", "./.git/",
    ],
    "steering_doc_path": (
        "/Users/dwillner/garvis/jacques-core/core-knowledge/core-system-knowledge/"
        "deepwiki-open-fork-steering.md"
    ),
    "steering_keywords": (
        "architecture", "overview", "provider", "client", "account", "pin", "isolation", "tool",
        "retrieval", "exclusion", "structure", "engine", "driver", "config", "manifest", "corpus",
        "sanitiz", "guard", "hardening", "fork", "upstream", "security",
    ),
    "structure_cache_path": "/tmp/deepwiki-open-self-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/deepwiki-open-self-wiki-pages-meta.json",
    "output_cache_path": "/tmp/deepwiki-open-self-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
