"""
Long-tail sweep, target 5/5 (last): the light-system-validator wiki. Standard repo-walk mode over
/Users/dwillner/garvis/projects/light-system-validator. Thin per-target config over the shared engine
(generate_wiki.py). PRE-STAGED (garvis-4p24 account block) — dry structure-fetch already verified
locally (no LLM cost), config is one-command-ready.

light-system-validator is a tiny, focused tool: a static schedule-overlap analyzer for the Home
Assistant lighting system, catching deploy-time conflicts where two routine automations write
conflicting program JSON to the same input_text.program_<light> entity (companion to the runtime
sanity-check script.validate_lighting_config). Single file (validate-schedule.js), no deps beyond
Node.js built-ins. Only two files total in this repo — the smallest target in this arc.

STEERING DOC: README.md (1974 bytes) is small but complete and genuinely owns the WHY — the EXACT bug
class it was built to catch (a real incident: nightlights_on_at_sunset vs sunset_bedside_fade_nightly
writing conflicting program state for main_bath_toilet/main_bath_shower), setup, exit codes, when to
run it, and an explicit "what it does NOT catch" limitations section. Given the repo's size, expect
the generated wiki to be correspondingly small (a handful of pages) — that is the right output for a
2-file tool, not a gap.

Exclusions: none needed — no node_modules/.venv/.git/scratch present in this checkout.

Account: waiting on garvis-4p24 resolution or CD's account-free window before firing. Courtesy sweep
via courtesy-sweep.sh first. Driver + export to be committed together, plain git.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/light-system-validator",
    "repo_description": (
        "light-system-validator — a static schedule-overlap analyzer for the Home Assistant lighting "
        "system. Catches deploy-time conflicts where two routine automations write conflicting "
        "program JSON to the same input_text.program_<light> entity (companion to the runtime "
        "sanity-check script.validate_lighting_config). Single file (validate-schedule.js), no "
        "dependencies beyond Node.js built-ins, uses HA's /api/states and "
        "/api/config/automation/config/<id> REST endpoints."
    ),
    "owner": "local",
    "repo": "light-system-validator",
    "excluded_dirs": [],
    "steering_doc_path": "/Users/dwillner/garvis/projects/light-system-validator/README.md",
    "steering_keywords": (
        "architecture", "overview", "schedule", "conflict", "automation", "validate", "home",
        "assistant", "lighting", "endpoint", "exit code", "template",
    ),
    "structure_cache_path": "/tmp/light-system-validator-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/light-system-validator-pages-meta.json",
    "output_cache_path": "/tmp/light-system-validator-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
