"""
garvis-nc7z: the bender wiki (remaining-repo sweep, last of the current queue). Standard repo-walk
mode over /Users/dwillner/garvis/projects/bender. Thin per-target config over the shared engine
(generate_wiki.py).

Bender is a drop-in replacement for @anthropic-ai/claude-agent-sdk: it translates query() calls into
`claude --bg` background-agent dispatches so existing CoPE-pipeline/Robodex code keeps running on
subscription quota billing instead of the post-2026-06-15 metered Agent SDK credit.

STEERING DOC: no README.md exists in this repo. Two candidates checked: bender.md (the vault
folder-note — 1837 bytes, a short mission/architecture pointer + a module-file list, mostly an index)
and HANDOFF.md (8555 bytes — the doc that actually owns the WHY: mission, "why it exists" section tied
to the June-15-2026 billing cutover, the mental model, a full walk of how query() works step-by-step,
a module map, and a "Load-bearing empirical findings (probed against real claude --bg)" section — the
genuine tribal-knowledge/rationale layer). HANDOFF.md is the clear choice; bender.md stays in-corpus as
an ordinary citable file.

Exclusions: node_modules/, coverage/, reports/ (stryker mutation output — reports/mutation/mutation.json
is small here, 612K total, well under the disallowed_relevant_files-class risk, but excluding the whole
scratch dir is cleaner than a per-file guard when the dir itself is pure build output), .git/ (this repo
has no own .git — part of the main garvis tree — kept for parity/safety anyway).

Account: fresh courtesy invariant-9 sweep run immediately before firing; server already pinned
DEEPWIKI_CLAUDE_ACCOUNT_DIR=/Users/dwillner/.claude-overflow-3 (claude-max-03@zentropi.ai). Git commit
via the sanctioned DEVELOPER_DIR=/Library/Developer/CommandLineTools interim prefix.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/bender",
    "repo_description": (
        "bender — a drop-in replacement for @anthropic-ai/claude-agent-sdk: translates query() calls "
        "into `claude --bg` background-agent dispatches so existing programmatic query() callers "
        "(the CoPE pipeline, Robodex) keep running on interactive-subscription quota billing instead "
        "of the post-2026-06-15 metered Agent SDK credit, via a one-line import swap, fully "
        "reversible. A pure translation layer, not a daemon: normalize prompt -> translate options -> "
        "pick account -> acquire concurrency slot -> dispatch `claude --bg` -> poll state.json -> "
        "parse the JSONL transcript -> synthesize SDK message events -> cleanup."
    ),
    "owner": "local",
    "repo": "bender",
    "excluded_dirs": ["./node_modules/", "./coverage/", "./reports/", "./.git/"],
    "steering_doc_path": "/Users/dwillner/garvis/projects/bender/HANDOFF.md",
    "steering_keywords": (
        "architecture", "overview", "translate", "dispatch", "poll", "transcript", "account", "pool",
        "concurrency", "multimodal", "hook", "max-turns", "empirical", "finding", "module", "mental",
        "model", "billing", "quota", "why",
    ),
    "structure_cache_path": "/tmp/bender-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/bender-pages-meta.json",
    "output_cache_path": "/tmp/bender-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
