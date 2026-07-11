"""
garvis-3cmi: the diderot wiki (back-burnered arc, the morph target's own record). Standard repo-walk
mode over /Users/dwillner/garvis/projects/diderot. Thin per-target config over the shared engine
(generate_wiki.py). Last of the current batch.

Diderot turns a hand-made customer-wiki corpus into cited, cross-linked pages by running each company
through a persistent Hindsight mental-model bank (compile -> export -> verify). This wiki documents
what EXISTS today as the record a future morph (deepwiki-open absorbing Hindsight concepts) resumes
from: the pure-core/I-O-wrapper split with its stryker TRUE-100% graduation, the compile/export/verify
loop, the two-input boundary design (compiled prose vs verbatim CRM metadata), and the hindsight-patch
(the SDK provider that lets Hindsight's LLM calls run on a Claude subscription instead of a metered key,
plus its own tool-isolation fix and per-role model tiering).

STEERING DOC: README.md owns the WHY directly — the GRADUATED status banner, the compile/export/verify
loop with its rationale, the deliberate two-input boundary (never route an exact identifier through an
LLM), and the 43-ready cross-link detection design. Picked README.md. hindsight-patch/claude_code_llm.py
also carries real design-rationale docstrings (the isolation-env choice, the subscription-auth pattern)
but stays in-corpus as an ordinary citable source file rather than a second steering doc — the engine
supports one steering_doc_path slot and README.md already owns the primary WHY.

Exclusions: ./diderot-output/ (generated wiki OUTPUT — 4 rendered company pages — not documentation
about the tool itself; same class as excluding a build artifact). disallowed_relevant_files guards
mutation.json (190KB stryker report — small, well under the 5-100MB risk class seen elsewhere, but
excluded for consistency: it's data, not documentation, and there's no reason it should ever be read
as a page source). No .git in this repo (part of the main garvis tree).

HONESTY NOTE (per the lead): the hindsight container backing this tool is currently DOWN (garvis-uzyr,
Dave-gated revival pending a token). If the corpus content surfaces that status (comments, docstrings),
it stays in the generated wiki — not scrubbed. Nothing in this config artificially suppresses it.

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
    "repo_path": "/Users/dwillner/garvis/projects/diderot",
    "repo_description": (
        "diderot — Hindsight-as-compiler for cited customer wiki pages: turns a hand-made customer "
        "corpus into cited, cross-linked wiki pages by running each company through a persistent "
        "Hindsight mental-model bank (compile.js -> export.js -> verify.js, a citation-first, "
        "Karpathy-minimal design with no agent fleet). The pure-core correctness modules "
        "(compile-core/export-core/verify-core) are stryker TRUE-100%-graduated; the I/O wrappers "
        "around them are behaviorally gated by integration suites instead. Includes hindsight-patch, "
        "an SDK provider that runs Hindsight's own LLM calls on a Claude subscription (never a "
        "metered key) with per-role model tiering and a tool-isolation fix. Currently a "
        "back-burnered arc — this wiki is the record a future morph (deepwiki-open absorbing "
        "Hindsight concepts) resumes from."
    ),
    "owner": "local",
    "repo": "diderot",
    "excluded_dirs": ["./diderot-output/", "./node_modules/", "./.git/"],
    "disallowed_relevant_files": ["mutation.json"],
    "steering_doc_path": "/Users/dwillner/garvis/projects/diderot/README.md",
    "steering_keywords": (
        "architecture", "overview", "compile", "export", "verify", "mental model", "hindsight",
        "citation", "graduat", "stryker", "provider", "isolation", "tiering", "boundary", "cross-link",
        "container", "morph",
    ),
    "structure_cache_path": "/tmp/diderot-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/diderot-pages-meta.json",
    "output_cache_path": "/tmp/diderot-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
