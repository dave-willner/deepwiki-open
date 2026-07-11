"""
Long-tail sweep, target 2/5: the example-generator wiki (the SDK_ISOLATION Node driver reference).
Standard repo-walk mode over /Users/dwillner/garvis/projects/example-generator. Thin per-target config
over the shared engine (generate_wiki.py). PRE-STAGED (garvis-4p24 account block) — dry structure-fetch
already verified locally (no LLM cost), config is one-command-ready.

example-generator is a synthetic CoPE training-data generator with two modes: single-policy (v1,
easy/hard x violation/non-violation matrix) and contrast mode (v2, recommended — authors examples IN
THE GAP between two policies, hardness defined by two-policy disagreement rather than author
self-rating, inspired by Samidh's contrast benchmark). Not part of the SDK review pipeline, but reuses
its engineering patterns (SDK isolation, atomic writes, content-addressed IDs, append-only artifacts,
hard-fail-no-fallback) — the Node-side SDK_ISOLATION reference the lead flagged.

STEERING DOC: PROJECT.md (30KB) owns the WHY directly — mode descriptions, the contrast-mode rationale
(hardness by two-policy disagreement, not self-rating), quick-start commands, and the explicit
engineering-pattern reuse note. PIPELINE-BUG-REPORT.md (10KB) is a real scar/incident doc but stays
in-corpus as an ordinary citable file rather than primary steering — PROJECT.md is the one doc that
actually frames the tool's purpose and design.

Exclusions: node_modules/ (real, present), outputs/ (76 entries of generated run data, not
documentation), coverage/ (test coverage report, build output), .git/ (no own .git — part of the main
garvis tree).

Account: waiting on garvis-4p24 resolution (overflow-3 auth) or CD's account-free window before firing
— this driver is ready the instant an account is clear. Courtesy sweep via courtesy-sweep.sh first,
same as every other target. Driver + export to be committed together, plain git.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/example-generator",
    "repo_description": (
        "example-generator — a synthetic CoPE training-data generator. Single-policy mode (v1): "
        "authors examples across an easy/hard x violation/non-violation matrix, difficulty "
        "self-rated by the generation agent. Contrast mode (v2, recommended for boundary-finding): "
        "given two policies, authors examples IN THE GAP between them — content that should receive "
        "opposite labels under each — hardness operationally defined by two-policy disagreement, not "
        "self-rating (inspired by Samidh's contrast benchmark). Not part of the SDK review pipeline, "
        "but reuses its engineering patterns (SDK isolation, atomic writes, content-addressed IDs, "
        "append-only artifacts, hard-fail-no-fallback)."
    ),
    "owner": "local",
    "repo": "example-generator",
    "excluded_dirs": ["./node_modules/", "./outputs/", "./coverage/", "./.git/"],
    "steering_doc_path": "/Users/dwillner/garvis/projects/example-generator/PROJECT.md",
    "steering_keywords": (
        "architecture", "overview", "contrast", "mode", "policy", "shape", "grade", "cope",
        "isolation", "sdk", "atomic", "content-addressed", "append-only", "hard-fail", "adjudicate",
        "difficulty", "boundary",
    ),
    "structure_cache_path": "/tmp/example-generator-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/example-generator-pages-meta.json",
    "output_cache_path": "/tmp/example-generator-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
