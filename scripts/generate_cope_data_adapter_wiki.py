"""
garvis-g9im: the cope-data-adapter wiki (CD's live production skill layer — the sanctioned single
bridge to cope_v3.db). Standard repo-walk mode (back to the normal pattern after garvis-9sfk's
manifest-corpus mode) — thin per-target config over the shared engine (generate_wiki.py).

Target is CD's ACTIVE production workspace. Read-only ingestion only: the dry structure-only fetch
(no LLM cost) was run first to confirm exclusions actually keep .venv/.pytest_cache/.ruff_cache/
mutants*/mutants.gate-aside-* out of the file_tree before any LLM call; nothing in this driver or the
shared engine ever writes into cope-data-adapter's own tree (wikicache + wikis/ export only, same as
every prior target).

STEERING DOC CHOICE (per the lead's "cite real paths, don't assume" instruction) — read all 4
skill-internal/*.md docs before picking:
  - SKILL-LAYER-GUIDANCE.md: its own header says "This package (`cope-tools`)..." — it documents the
    COPE-TOOLS package's classify/relabel/optimize skill contract, not cope-data-adapter itself. It
    was the right EXTERNAL steering doc for the cope-tools-py wiki (garvis-9khs); it is the WRONG
    primary steering doc here (wrong package), even though it physically lives in this repo's
    skill-internal/ dir. Left as ordinary corpus content — a real file the LLM can still cite.
  - JS-PIPELINE-CONVERGENCE.md: documents CLR/Pareto convergence-loop fidelity to the JS pipeline —
    relevant background (export_rung/reconcile_variant_clr feed that loop) but pipeline-level, not
    adapter-specific. Ordinary corpus content, not the primary steering doc.
  - DEBUGGING.md: a temporary, self-shrinking troubleshooting playbook — useful as a cited page
    source, not a WHY/design-rationale doc.
  - INTERNAL-OPS.md (689 lines) — CHOSEN. This is the one doc genuinely ABOUT cope-data-adapter's own
    role: "the ONLY database surface... never touch cope_v3.db with raw sqlite — the adapter is the
    one sanctioned bridge, and its guards are the fence", plus concrete scars (e.g. the VL-S1
    --effective/COALESCE-latest lesson). Inlined client-side per-page, same mechanism as every prior
    wiki (never through the server's relevant_files, whose path-traversal guard correctly refuses
    paths outside repo_path — moot here since it's inside repo_path, but kept for parity/consistency).

Account: fresh courtesy invariant-9 sweep run immediately before firing (see dialog); server already
pinned DEEPWIKI_CLAUDE_ACCOUNT_DIR=/Users/dwillner/.claude-overflow-3 (claude-max-03@zentropi.ai).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/cope-data-adapter",
    "repo_description": (
        "cope-data-adapter — the ONE sanctioned bridge to the canonical cope_v3.db (never touch it "
        "with raw sqlite): read-only export (export_rung, fetch_policy), insert-only ingestion "
        "(import_v3, insert_only, ingest_results, record_winner, record_correction), variant-label "
        "propagation and reconciliation against CLR (propagate_variant_labels, "
        "reconcile_variant_clr), provenance and envelope verification (provenance, verify_envelope), "
        "and policy-text sync (sync_policy_text). CD's live production workspace."
    ),
    "owner": "local",
    "repo": "cope-data-adapter",
    "excluded_dirs": [
        "./.venv/", "./.pytest_cache/", "./.ruff_cache/", "./mutants/",
        "./mutants.gate-aside-1783291594/", "./.git/",
    ],
    "steering_doc_path": (
        "/Users/dwillner/garvis/projects/cope-data-adapter/skill-internal/INTERNAL-OPS.md"
    ),
    "steering_keywords": (
        "adapter", "bridge", "cope_v3", "database", "db", "insert-only", "export", "import",
        "provenance", "envelope", "correction", "winner", "variant", "reconcile", "clr", "policy",
        "sync", "guard", "scar", "overview", "architecture", "safety",
    ),
    "structure_cache_path": "/tmp/cope-data-adapter-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/cope-data-adapter-pages-meta.json",
    "output_cache_path": "/tmp/cope-data-adapter-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
