"""
garvis-9sfk: the Distaff design-surface wiki (ekve.3 / wiki-registry row 5, baseline generation).

MANIFEST-CORPUS MODE (JM ruling, OPTION 1) — different from every prior thin config in this
directory. Every earlier wiki (cope-tools-py, JS pipeline, jacques-core-hooks, jacques-core-system)
pointed `repo_path` at a REAL repo directory and let the shared engine's structure-determination walk
it (server-side excluded_dirs/included_dirs, garvis-11z.17). The Distaff design surface is NOT a
contiguous directory — it's a curated, cross-tree set (role docs under core-hooks/roles/, the
bicameral skill under core-skills/, design-record docs under core-knowledge/, plus bead/decision text
that isn't a file at all) — and the scope ruling requires that per-file CODE (already covered by
wikis/jacques-core-system + wikis/jacques-core-hooks) be STRUCTURALLY absent, not just avoided by
convention.

Mechanism chosen (mine to pick, per the dispatch): build a CORPUS STAGING DIRECTORY
(`corpus/distaff/`) that becomes `repo_path` for this run. It contains ONLY:
  - symlinks to the real provenance files (role docs, bicameral.md, fleet-invariants.md,
    thread-lifecycle-procedures.md, conv-format-ladder.md, ledger-taxonomy.js, one representative
    beads-decisions view) — symlinks, never copies, per the 2026-06-26 no-duplicate-copies ruling.
  - rendered `bd show <id>` text files for the named scar/design beads (garvis-532 epic body,
    532.336/338/339, tv0l, f2kz, 4bjl, 1nhu.5) — materialized DB content as corpus text, same pattern
    the steering doc itself already uses for its own provenance.
No code file from the real jacques-core tree is symlinked in, so LINK-not-recover is enforced by the
corpus's construction, not by prompt instruction alone. See corpus/distaff/MANIFEST.md for the exact
file list + bead ids (verbatim record for JM's ekve.3 registry row).

The shared engine (`generate_wiki.py`) runs UNCHANGED — it only ever needed `repo_path` to be *some*
local directory `/local_repo/structure` + `get_local_files_context` can read, and a corpus staging
directory satisfies that contract exactly like a real repo would. No engine surgery was needed.

Steering: jacques-core/core-knowledge/core-system-knowledge/distaff-wiki-steering.md (CoS-authored,
2026-07-10), inlined per-page client-side — same mechanism as every prior run (never through the
server's relevant_files/get_local_files_context, whose path-traversal guard correctly refuses paths
outside repo_path).

Account: this run's target server process is already running with
DEEPWIKI_CLAUDE_ACCOUNT_DIR=/Users/dwillner/.claude-overflow-3 (verified via `ps eww` against the live
PID before firing) — identity=claude-max-03@zentropi.ai, confirmed via `claude auth status` under that
CLAUDE_CONFIG_DIR with CLAUDE_CODE_OAUTH_TOKEN/ANTHROPIC_API_KEY/CLAUDE_SECURESTORAGE_CONFIG_DIR
blanked (the cope-tools-py account-pin pattern, garvis-9sfk gate item "identity=claude-max-03").
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/deepwiki-open/corpus/distaff",
    "repo_description": (
        "the Distaff — Dave Willner's fleet of Spindles (multi-thread agents: Decision/Execution/"
        "Attention/Evaluation as four voices of one agent), documented as a SYSTEM/DESIGN surface: "
        "the four-thread model and charters, the lifecycle state machine (spawn/wake/hibernate/stage/"
        "evacuate + lock/holder/backstage), the liveness/identity truth model, the delivery/triage "
        "layer (phone/inboxes/urgency_note/fleet-update), the DCS ledger taxonomy + beads-write "
        "discipline, and the authority model (command-by-negation, manager pointers, goal-doc lock, "
        "fleet invariants). This is a CURATED CORPUS, not a repo walk — per-file code is deliberately "
        "absent (it is already documented in the separate jacques-core-system and jacques-core-hooks "
        "wikis, which this wiki must LINK to, never re-cover)."
    ),
    "owner": "local",
    "repo": "distaff",
    "excluded_dirs": ["./.git/"],  # the corpus dir has no real code/vcs noise; kept for parity/safety
    "steering_doc_path": (
        "/Users/dwillner/garvis/jacques-core/core-knowledge/core-system-knowledge/"
        "distaff-wiki-steering.md"
    ),
    "steering_keywords": (
        "four-thread", "spindle", "decision", "execution", "attention", "evaluation", "lifecycle",
        "spawn", "wake", "hibernate", "stage", "evacuate", "lock", "liveness", "identity", "pane",
        "delivery", "phone", "inbox", "triage", "urgency", "ledger", "beads", "authority", "invariant",
        "command", "manager", "scar", "overview", "architecture",
    ),
    "structure_cache_path": "/tmp/distaff-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/distaff-pages-meta.json",
    "output_cache_path": "/tmp/distaff-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
