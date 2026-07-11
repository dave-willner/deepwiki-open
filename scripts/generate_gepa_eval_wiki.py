"""
Long-tail sweep, target 3/5: the gepa-eval wiki. Standard repo-walk mode over
/Users/dwillner/garvis/projects/gepa-eval. Thin per-target config over the shared engine
(generate_wiki.py). PRE-STAGED (garvis-4p24 account block) — dry structure-fetch already verified
locally (no LLM cost), config is one-command-ready.

gepa-eval is a vendored fork of the upstream open-source `gepa-ai/gepa` framework (Genetic-Pareto:
optimize any text parameter — prompts, code, agent architectures — via LLM-based reflection + Pareto-
aware evolutionary search), with a Zentropi-specific integration layered on top: `cope_optimizer.py`
(top-level driver, runs GEPA optimization on content-labeling policies, uses CoPE as the evaluator +
P1/P2/P5 agent prompts as custom mutation operators) and `src/gepa/adapters/cope_adapter/` (our own
adapter module: zentropi_client, proposers).

STEERING: no dedicated "why we integrated GEPA for CoPE" doc exists — flagging that honestly rather
than inventing a steering doc that doesn't reflect real authored content. README.md (30KB) is
upstream's own general-purpose framework overview (GEPA's mission, key results, quick start) — kept as
steering anyway since it's the closest thing to a WHY layer this repo carries, and genuinely useful
orientation for a reader who doesn't know what GEPA is. The Zentropi-specific integration content
(cope_optimizer.py, cope_adapter.py) stays in-corpus as ordinary citable source files; the wiki
structure-determination step is expected to naturally surface it as its own page given how the repo
description below foregrounds it.

Exclusions: __pycache__/, .venv/, .git/ (real, own git — vendored fork), docs/ (21MB — upstream's own
full mkdocs documentation SITE, publicly published on gepa-ai.github.io already; not our fork-specific
content, and would dominate/bloat the corpus with redundant upstream material if included).

Account: waiting on garvis-4p24 resolution or CD's account-free window before firing. Courtesy sweep
via courtesy-sweep.sh first. Driver + export to be committed together, plain git.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/gepa-eval",
    "repo_description": (
        "gepa-eval — a vendored fork of the open-source gepa-ai/gepa framework (Genetic-Pareto: "
        "optimize any text parameter — prompts, code, agent architectures, configurations — via "
        "LLM-based reflection and Pareto-efficient evolutionary search), layered with a "
        "Zentropi-specific integration for optimizing CoPE content-labeling policies: "
        "cope_optimizer.py (the top-level driver, uses CoPE as the evaluator and custom P1/P2/P5 "
        "agent-prompt mutation operators) and src/gepa/adapters/cope_adapter/ (zentropi_client, "
        "proposers — our own adapter module bridging GEPA's optimize_anything API to CoPE)."
    ),
    "owner": "local",
    "repo": "gepa-eval",
    "excluded_dirs": ["./__pycache__/", "./.venv/", "./.git/", "./docs/"],
    "steering_doc_path": "/Users/dwillner/garvis/projects/gepa-eval/README.md",
    "steering_keywords": (
        "architecture", "overview", "optimize", "reflection", "pareto", "evolution", "cope",
        "adapter", "zentropi", "proposer", "mutation", "policy", "evaluator", "engine",
    ),
    "structure_cache_path": "/tmp/gepa-eval-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/gepa-eval-pages-meta.json",
    "output_cache_path": "/tmp/gepa-eval-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
