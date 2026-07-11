"""
Long-tail sweep, target 1/5: the openwiki wiki (Dave-relevant — the comparison/pattern-source repo he
wanted evaluated). Standard repo-walk mode over /Users/dwillner/garvis/projects/openwiki. Thin
per-target config over the shared engine (generate_wiki.py).

OpenWiki (langchain-ai/openwiki) is a comparable tool to our own deepwiki-open fork: a TypeScript CLI
that writes/maintains repo documentation via an agent-driven workflow (DeepAgents local-shell backend,
multi-provider model support). Notably, this repo has already run itself on itself — it carries a real
`openwiki/` directory of self-generated documentation (quickstart + architecture/cli/agent/operations
notes), which is genuine curated content, not scratch — left in-corpus.

STEERING DOC: openwiki/quickstart.md — OpenWiki's OWN generated top-level doc, exactly the WHY/overview
layer (what the repo does, where each subsystem lives, key source files) a tool like this is designed
to produce. Using the tool's own self-documentation as our steering doc is apt here specifically because
this target repo IS a documentation tool; its own output is the most authoritative WHY source available,
more so than README.md (which is a shorter user-facing install/usage blurb). The deeper linked docs
(architecture/overview.md, cli/usage.md, agent/workflow.md, operations/credentials-and-updates.md) stay
in-corpus as ordinary citable files rather than a second steering doc.

Exclusions: dist/ (build output), node_modules/, .git/.

Account: fresh courtesy invariant-9 sweep run immediately before firing; server restarted post-hold,
pinned DEEPWIKI_CLAUDE_ACCOUNT_DIR=/Users/dwillner/.claude-overflow-3 (claude-max-03@zentropi.ai). Git
commit via plain git now (DEVELOPER_DIR interim retired — CC pinned back to 2.1.206), driver + export
committed together.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/openwiki",
    "repo_description": (
        "OpenWiki (langchain-ai/openwiki) — a TypeScript CLI that writes and maintains repository "
        "documentation via an agent-driven workflow: an Ink-based interactive terminal app, a "
        "DeepAgents local-shell backend rooted at the target repository, multi-provider model support "
        "(OpenRouter/Anthropic/OpenAI/Baseten/Fireworks), and scheduled GitHub Actions updates. A "
        "comparable tool to our own deepwiki-open fork, being documented here as an evaluation "
        "pattern-source."
    ),
    "owner": "local",
    "repo": "openwiki",
    "excluded_dirs": ["./dist/", "./node_modules/", "./.git/"],
    "steering_doc_path": "/Users/dwillner/garvis/projects/openwiki/openwiki/quickstart.md",
    "steering_keywords": (
        "architecture", "overview", "cli", "agent", "workflow", "credential", "provider", "model",
        "command", "prompt", "run", "update", "init", "deepagents", "shell", "backend",
    ),
    "structure_cache_path": "/tmp/openwiki-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/openwiki-pages-meta.json",
    "output_cache_path": "/tmp/openwiki-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
