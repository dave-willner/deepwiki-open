"""Claude Code (Max subscription) ModelClient integration.

Generation provider that runs on a **Claude Max subscription via the Claude Agent SDK** — never a metered
API key, never a third-party proxy. Code never leaves the machine: the SDK spawns the local `claude` CLI as
a subprocess and authenticates via that CLI's own OAuth credentials.

★ ACCOUNT PIN (Dave-direct, 2026-07-03): this provider is PINNED to a dedicated headless Max account
(`overflow-2` / `claude-max-01@zentropi.ai`, or `overflow-3` / `claude-max-02@zentropi.ai` as backup) —
it must NEVER run against Dave's personal account (`main` or `overflow-1`, both `dave@zentropi.ai`; the
personal account's usage/rate-limits must not be touched by automated doc-generation traffic).

THE ENV-MERGE TRAP (load-bearing — see `cope_tools.adapters.claude_agent` for the original finding):
`ClaudeAgentOptions.env` MERGES onto the full inherited `os.environ`, it does NOT replace it. So pinning
`CLAUDE_CONFIG_DIR` alone is not dispositive: an ambient `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`
in the parent process's environment would still win the CLI's own auth precedence over the pinned config
dir's credentials file. The fix (replicated here): explicitly blank both to `""` in the env dict passed to
`ClaudeAgentOptions`, which forces the CLI to fall through to file-based auth via
`<pinned_dir>/.credentials.json` — the same mechanism `~/.claude` uses ambiently with no token env set.
`CLAUDE_SECURESTORAGE_CONFIG_DIR=""` is the Diderot keychain-namespacing fix (see
`projects/diderot/hindsight-patch/claude_code_llm.py`): without it, a non-default `CLAUDE_CONFIG_DIR`'s
OAuth keychain lookup gets namespaced by `sha256(CLAUDE_CONFIG_DIR)` and fails.

Embeddings are explicitly out of scope for this provider (Slice 2 uses local Ollama instead) —
`convert_inputs_to_api_kwargs`/`call`/`acall` all raise `NotImplementedError` for `ModelType.EMBEDDER`.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import anyio
from adalflow.core.model_client import ModelClient
from adalflow.core.types import ModelType

log = logging.getLogger(__name__)

# The two dedicated headless Max accounts this provider is allowed to run against. Both were empirically
# verified (via `claude auth status` with CLAUDE_CONFIG_DIR pinned + ambient token/key blanked) to be
# genuinely distinct accounts from Dave's personal one:
#   main            (~/.claude)            -> dave@zentropi.ai        (Dave's personal account)
#   overflow-1      (~/.claude-overflow)   -> dave@zentropi.ai        (same personal account, forbidden)
#   overflow-2      (~/.claude-overflow-2) -> claude-max-01@zentropi.ai  (PIN TARGET)
#   overflow-3      (~/.claude-overflow-3) -> claude-max-02@zentropi.ai  (backup)
OVERFLOW_2_CONFIG_DIR = str(Path("/Users/dwillner/.claude-overflow-2"))
OVERFLOW_3_CONFIG_DIR = str(Path("/Users/dwillner/.claude-overflow-3"))
_ALLOWED_ACCOUNT_DIRS = [OVERFLOW_2_CONFIG_DIR, OVERFLOW_3_CONFIG_DIR]

DEFAULT_MODEL = "claude-sonnet-4-6"


class DisallowedAccountDirError(Exception):
    """Fail-closed guard: the requested Claude config dir is not one of the allowed dedicated headless
    accounts. Raised at CONSTRUCTION time — before any query — so a misconfigured caller refuses loud
    instead of silently burning Dave's personal account (main/overflow-1)."""


def _normalize_dir(path: str) -> str:
    """Path-identity normalization for the allow-list comparison — `expanduser` only, deliberately NOT
    `.resolve()` (mirrors `cope_tools.adapters.claude_agent._normalize_dir`): we compare the directory
    IDENTITY the caller named, not its resolved target."""
    return str(Path(path).expanduser())


def _account_env(account_config_dir: str) -> Dict[str, str]:
    """The pin-and-blank env override (the env-merge trap fix). Pins `CLAUDE_CONFIG_DIR` to the dedicated
    account dir AND strips any inherited `CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_API_KEY` to `""` — the strip
    is what makes the pin dispositive, since `ClaudeAgentOptions.env` merges onto (not replaces) the full
    inherited process environment."""
    return {
        "CLAUDE_CONFIG_DIR": account_config_dir,
        "CLAUDE_CODE_OAUTH_TOKEN": "",
        "ANTHROPIC_API_KEY": "",
        "CLAUDE_SECURESTORAGE_CONFIG_DIR": "",
    }


class ClaudeCodeClient(ModelClient):
    __doc__ = r"""A ModelClient wrapper for Claude Max, driven by the Claude Agent SDK.

    Pinned to a dedicated headless Max account (never Dave's personal account) — see the module docstring
    for the full rationale.

    Example:
        ```python
        from api.claude_code_client import ClaudeCodeClient

        client = ClaudeCodeClient()  # defaults to the overflow-2 pin
        generator = adal.Generator(
            model_client=client,
            model_kwargs={"model": "claude-sonnet-4-6"}
        )
        ```
    """

    def __init__(
        self,
        account_config_dir: str = OVERFLOW_2_CONFIG_DIR,
        model: str = DEFAULT_MODEL,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the Claude Code (Max) client, pinned to a dedicated headless account.

        Args:
            account_config_dir: the Claude CLI config directory (and therefore account) to pin to. MUST be
                one of the allowed dedicated headless account dirs — anything else (including main or
                overflow-1) raises `DisallowedAccountDirError` immediately.
            model: default model id used when a call doesn't specify one.

        Raises:
            DisallowedAccountDirError: if `account_config_dir` is not an allowed dedicated account dir.
        """
        super().__init__(*args, **kwargs)

        normalized = _normalize_dir(account_config_dir)
        allowed_normalized = [_normalize_dir(d) for d in _ALLOWED_ACCOUNT_DIRS]
        if normalized not in allowed_normalized:
            raise DisallowedAccountDirError(
                f"ClaudeCodeClient: refusing — account_config_dir {account_config_dir!r} is not one of the "
                f"allowed dedicated headless accounts {_ALLOWED_ACCOUNT_DIRS!r}. This provider must never "
                f"run against Dave's personal account (main/overflow-1)."
            )

        self._account_config_dir = account_config_dir
        self._default_model = model
        self._env = _account_env(account_config_dir)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create an instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "account_config_dir": self._account_config_dir,
            "model": self._default_model,
        }

    def __getstate__(self):
        """No live SDK handle is held between calls (the SDK spawns a fresh subprocess per query), so
        there's nothing non-picklable to strip — kept for interface parity with sibling clients
        (bedrock/azure), which DO hold live handles."""
        return self.__dict__.copy()

    def __setstate__(self, state):
        self.__dict__.update(state)

    def convert_inputs_to_api_kwargs(
        self, input: Any = None, model_kwargs: Optional[Dict] = None, model_type: Optional[ModelType] = None
    ) -> Dict:
        """Convert inputs to API kwargs for the Claude Agent SDK."""
        model_kwargs = model_kwargs or {}

        if model_type == ModelType.LLM:
            return {
                "model": model_kwargs.get("model", self._default_model),
                "input": input,
            }
        elif model_type == ModelType.EMBEDDER:
            raise NotImplementedError(
                "ClaudeCodeClient does not support embeddings — use the Ollama embedder provider instead."
            )
        else:
            raise ValueError(f"Model type {model_type} is not supported by ClaudeCodeClient")

    async def acall(self, api_kwargs: Optional[Dict] = None, model_type: Optional[ModelType] = None) -> Any:
        """Make an asynchronous generation call via the Claude Agent SDK, pinned to the dedicated account."""
        api_kwargs = api_kwargs or {}

        if model_type == ModelType.EMBEDDER:
            raise NotImplementedError(
                "ClaudeCodeClient does not support embeddings — use the Ollama embedder provider instead."
            )
        if model_type != ModelType.LLM:
            raise ValueError(f"Model type {model_type} is not supported by ClaudeCodeClient")

        # Lazy import so the absence of claude_agent_sdk doesn't break other providers at module import time.
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

        model = api_kwargs.get("model", self._default_model)
        prompt = api_kwargs.get("input", "")

        options = ClaudeAgentOptions(
            max_turns=1,
            allowed_tools=[],
            model=model,
            setting_sources=[],
            cwd="/tmp",
            disallowed_tools=["mcp__claude_ai_*"],
            env=self._env,
        )

        full_text = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_text += block.text

        return full_text

    def call(self, api_kwargs: Optional[Dict] = None, model_type: Optional[ModelType] = None) -> Any:
        """Make a synchronous generation call — bridges to the async SDK via `anyio.run`."""
        return anyio.run(self.acall, api_kwargs, model_type)
