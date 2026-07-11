"""
garvis-bc9k: the superhuman-cli wiki (daily-driver email tooling). Standard repo-walk mode over
/Users/dwillner/garvis/projects/superhuman-cli. Thin per-target config over the shared engine
(generate_wiki.py).

superhuman-cli is a CLI + MCP server controlling Superhuman (Dave's daily email client) via Chrome
DevTools Protocol. NOTE ON SENSITIVITY: this repo's files are permission-restricted (600/700, unlike
every prior target) — it is Dave's personal daily-driver tool, not shared project code. This run makes
the same Claude Agent SDK call every other wiki in this arc makes (local machine, no third-party
proxy, no metered key) — nothing new leaves the machine beyond the normal SDK call. Flagged explicitly
rather than silently proceeding.

EXCLUSIONS: node_modules/, dist/ (contains a 5.5MB bundled index.js — build output, not source),
.claude/ (local Claude Code settings, not documentation), scratch/ (named scratch — investigation
throwaways), .git/. The repo root also has a loose 1.1MB `superhuman-main` BINARY executable that
excluded_dirs can't catch (it's a file, not a directory) — added to disallowed_relevant_files so it can
never be selected as a relevant_file and read into a prompt (same class of risk as auto-doc's
mutation.json, garvis-gj8z).

NOT excluded, deliberately: the ~60 loose top-level debug-*.ts/explore-*.ts/find-*.ts/check-*.ts
investigation scripts at repo root. They're harmless as file_tree listing entries (plain TypeScript,
not secrets) and excluded_dirs can't target loose files anyway; letting structure-determination's own
"most logical structure" judgment route around them (toward src/, README.md, docs/) is proportionate —
building per-file exclusion machinery for ~60 individually-named scripts is not.

STEERING DOC: README.md is the CLI-usage doc (setup, command reference) — useful content, not the WHY
layer. CLAUDE.md is the doc that owns the WHY: the active-account precedence chain, the canonical
single-resolver pattern (getEffectiveActiveAccount(), preventing precedence drift across three
historical direct readers), and Bun-vs-Node conventions. Picked CLAUDE.md.

Account: fresh courtesy invariant-9 sweep run immediately before firing; server already pinned
DEEPWIKI_CLAUDE_ACCOUNT_DIR=/Users/dwillner/.claude-overflow-3 (claude-max-03@zentropi.ai). Git commit
via the sanctioned DEVELOPER_DIR=/Library/Developer/CommandLineTools interim prefix — driver committed
in the same breath as the export this time (garvis-nc7z pre-close finding).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_wiki import run  # noqa: E402

CONFIG = {
    "repo_path": "/Users/dwillner/garvis/projects/superhuman-cli",
    "repo_description": (
        "superhuman-cli — a CLI and MCP server that controls Superhuman (a macOS email client) via "
        "Chrome DevTools Protocol: read/search/reply/send/archive/snooze email, manage calendar "
        "events, contacts, labels, snippets, and multi-account switching, with an MCP tool surface "
        "for agent-driven email operations. Dave's daily-driver email tooling."
    ),
    "owner": "local",
    "repo": "superhuman-cli",
    "excluded_dirs": ["./node_modules/", "./dist/", "./.claude/", "./scratch/", "./.git/"],
    "disallowed_relevant_files": ["superhuman-main"],
    "steering_doc_path": "/Users/dwillner/garvis/projects/superhuman-cli/CLAUDE.md",
    "steering_keywords": (
        "architecture", "overview", "account", "mcp", "tool", "cdp", "chrome", "devtools", "resolver",
        "precedence", "draft", "send", "auth", "provider", "connection", "token", "crypto",
    ),
    "structure_cache_path": "/tmp/superhuman-cli-wiki-structure-raw.txt",
    "pages_meta_path": "/tmp/superhuman-cli-pages-meta.json",
    "output_cache_path": "/tmp/superhuman-cli-wiki-full.json",
}

if __name__ == "__main__":
    run(CONFIG)
