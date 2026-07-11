"""
Long-tail sweep, target 4/5: the DeepReason wiki. Standard repo-walk mode over
/Users/dwillner/garvis/projects/DeepReason. Thin per-target config over the shared engine
(generate_wiki.py). PRE-STAGED (garvis-4p24 account block) — dry structure-fetch already verified
locally (no LLM cost), config is one-command-ready.

DeepReason is a harness that makes an LLM argue with itself, on the record: given a hard "why"
question, it conjectures a spread of bold explanations, then criticizes them (each candidate states
what evidence would refute it, weak ones get argued down, survivors compete head-to-head), with the
whole exchange written to an append-only, byte-for-byte replayable log. A deterministic harness does
all bookkeeping and decides nothing on vibes. Two ways to run it: the full harness (all the machinery)
and MiniReason (the measured ~20% that carries most of the value, in ~900 lines).

STEERING DOC: README.md (7.4KB) owns the WHY directly and clearly — the whole design philosophy
(conjecture-then-criticize, evidence-that-would-refute, the full-harness-vs-MiniReason choice framed
as "the most important decision"), quickstart for both modes, and an MCP tool-surface pointer.
docs/ (228K, 16 real authored design docs — CONTROLLER_SPEC.md, TOKEN_ECONOMY.md,
STATE_OF_THE_THEORY.md, harness-spec-v1.3.md, etc.) is genuinely OUR OWN design documentation, not a
redundant upstream site (unlike gepa-eval's docs/) — kept in-corpus as real citable content.

Exclusions: .git/ only (no node_modules/.venv/outputs present in this checkout).

Account: waiting on garvis-4p24 resolution or CD's account-free window before firing. Courtesy sweep
via courtesy-sweep.sh first. Driver + export to be committed together, plain git.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/DeepReason",
    "repo_description": (
        "DeepReason — a harness that makes an LLM argue with itself, on the record: given a hard "
        "open 'why' question, it conjectures a spread of bold explanations, then criticizes them "
        "(each candidate states what evidence would refute it, weak ones get argued down, survivors "
        "compete head-to-head), with the whole exchange written to an append-only, byte-for-byte "
        "replayable log. A deterministic harness does all the bookkeeping and decides nothing on "
        "vibes; the output is a map of which explanations survived scrutiny and why. Two run modes: "
        "the full harness (all the machinery) and MiniReason (the measured ~20% that carries most of "
        "the value, in ~900 lines)."
    ),
    "owner": "local",
    "repo": "DeepReason",
    "excluded_dirs": ["./.git/"],
    "steering_doc_path": "/Users/dwillner/garvis/projects/DeepReason/README.md",
    "steering_keywords": (
        "architecture", "overview", "conjecture", "criticize", "harness", "minireason", "controller",
        "token", "economy", "cache", "replay", "log", "agent", "mcp", "run", "thesis", "engine",
    ),
    "structure_cache_path": "/tmp/deepreason-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/deepreason-pages-meta.json",
    "output_cache_path": "/tmp/deepreason-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
