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

★ TOOL ISOLATION — `tools=[]` is the field that actually disables built-in tools (Bash, Read, Write, Edit,
...); `allowed_tools=[]` does NOT (per the SDK's own docstring: "Tool names auto-allowed WITHOUT PROMPTING
for permission... To restrict which tools are available AT ALL, use `tools` instead."). Found empirically,
Slice 3/4 gate testing: with only `allowed_tools=[]` set (no `tools=[]`), a sufficiently long/complex prompt
provoked the model into calling the real Bash tool — `find`, `ls`, `cat` — actually executing and exploring
the filesystem (including another session's unrelated files under `cwd="/tmp"`), consuming turns until
`max_turns` was exhausted. `tools=[]` alone (even at `max_turns=1`) fully suppresses this: zero tool calls,
the model instead correctly reports it lacks the file content rather than fetching it via Bash. BOTH fields
are now set (`tools=[]` is the one doing the real work; `allowed_tools=[]` kept for defense-in-depth/parity
with the precedent files, which — misleadingly — used only `allowed_tools=[]` and never actually verified
tool isolation empirically).
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

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


class DisallowedAccountIdentityError(DisallowedAccountDirError):
    """Fail-closed guard (garvis-dip0): the pinned DIRECTORY passed the allow-list, but the ACCOUNT
    IDENTITY resolved from it is not an allowed dedicated headless account — e.g. the pinned dir was
    re-logged into Dave's personal account after the fact, or into some other unexpected account. The
    directory allow-list alone does not catch this: it checks WHICH FOLDER was named, never WHO that
    folder's credentials actually authenticate as. Subclasses `DisallowedAccountDirError` so any
    existing caller that catches that already catches this too."""


# Personal identities this provider must never run as, checked by exact match.
_PERSONAL_EMAIL_DENYLIST = frozenset({"dave.willner@gmail.com", "dave@zentropi.ai"})

# Positive pattern for a genuinely dedicated headless account (defense-in-depth beyond the denylist
# above — refuses ANY identity that isn't shaped like one of these, not just the two known personal
# addresses, so a typo'd or newly-added unexpected account is refused too, not silently allowed).
_DEDICATED_ACCOUNT_EMAIL_PATTERN = re.compile(r"^claude-max-\d+@zentropi\.ai$")


def _default_identity_probe(account_config_dir: str) -> Dict[str, Any]:
    """Real probe: run `claude auth status` under the exact pinned+blanked env this client would use
    for generation, and return the parsed JSON identity. Costs one subprocess spawn (a few hundred ms)
    — `auth status` never calls the model API, so this consumes zero quota."""
    env = {**os.environ, **_account_env(account_config_dir)}
    result = subprocess.run(
        ["claude", "auth", "status"], env=env, capture_output=True, text=True, timeout=15, check=True
    )
    return json.loads(result.stdout)


def _assert_identity_allowed(account_config_dir: str, probe: Callable[[str], Dict[str, Any]]) -> None:
    """Resolve the pinned dir's real account identity via `probe` and refuse (loud, before any query)
    unless it is BOTH not on the personal denylist AND shaped like a dedicated `claude-max-N@zentropi.ai`
    account. Raises `DisallowedAccountIdentityError` (never returns a "maybe") on any other identity,
    including a probe reporting `loggedIn: False`."""
    status = probe(account_config_dir)
    email = status.get("email") or ""
    is_denylisted = email in _PERSONAL_EMAIL_DENYLIST
    is_dedicated_shape = bool(_DEDICATED_ACCOUNT_EMAIL_PATTERN.match(email))
    if is_denylisted or not is_dedicated_shape:
        raise DisallowedAccountIdentityError(
            f"ClaudeCodeClient: refusing — account_config_dir {account_config_dir!r} resolved to "
            f"identity {email!r}, which is either on the personal-account denylist or does not match "
            "the dedicated headless account pattern (claude-max-N@zentropi.ai). This provider must "
            "never run against Dave's personal account."
        )


def _normalize_dir(path: str) -> str:
    """Path-identity normalization for the allow-list comparison — `expanduser` only, deliberately NOT
    `.resolve()` (mirrors `cope_tools.adapters.claude_agent._normalize_dir`): we compare the directory
    IDENTITY the caller named, not its resolved target."""
    return str(Path(path).expanduser())


_NO_THINK_PREFIX = "/no_think "


def _strip_no_think_prefix(prompt: str) -> str:
    """Strip this app's universal `"/no_think "` prompt prefix (garvis-ulki) — a Qwen/Ollama
    thinking-mode-suppression directive (`simple_chat.py`/`websocket_wiki.py` build every provider's
    prompt as `f"/no_think {system_prompt}"` unconditionally), meaningless to Claude. Previously this
    reached the CLI and had to be defused with `_guard_leading_slash`'s leading-space trick (see
    below); stripping it outright is cleaner — no noise-prefix reaches the model at all, and it
    removes this specific artifact from the leading-slash-guard's job entirely. Only strips the EXACT
    literal `"/no_think "` prefix (with its trailing space, matching exactly how this app always
    constructs it) — never touches a prompt that merely starts with a similarly-named but different
    word (e.g. `"/no_thinking_about_it"`), and never touches prompts that don't have this prefix."""
    if prompt.startswith(_NO_THINK_PREFIX):
        return prompt[len(_NO_THINK_PREFIX):]
    return prompt


def _guard_leading_slash(prompt: str) -> str:
    """Defuse the CLI slash-command footgun (found empirically, Slice 2 gate testing): unlike every other
    provider in this app (a plain HTTP chat-completion API), `ClaudeCodeClient` drives the actual `claude`
    CLI's interactive REPL via the SDK. A prompt whose first non-whitespace character is `/` gets parsed as
    a CLI SLASH COMMAND instead of being treated as prompt text — the CLI then silently returns
    `"Unknown command: /whatever"` as if it were a normal response, no exception, so a naive caller would
    ship that as the generated wiki content. This was FIRST found via this app's universal `/no_think`
    prompt prefix (built for Qwen/Ollama's thinking-mode suppression, applied to every provider
    unconditionally) — that specific artifact is now stripped outright before it ever reaches here (see
    `_strip_no_think_prefix`, garvis-ulki), but this guard remains as the general backstop for any OTHER
    leading-slash prompt this app might construct. Verified fix: a single leading space defuses the
    slash-command parser while leaving the semantic content fully intact (confirmed: the model correctly
    read and echoed the guarded text back). Only touches prompts that would otherwise misfire; never alters
    prompt content for prompts that don't start with `/`."""
    if prompt.startswith("/"):
        return " " + prompt
    return prompt


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


_SCRATCH_DIR_PREFIX = "deepwiki-agent-cwd-"


def _new_scratch_cwd() -> str:
    """Per-spawn isolation cwd (garvis-11z.12.18.7 gate finding, replaces the old hardcoded
    `cwd="/tmp"`): the SDK-bundled `claude` binary runs a recursive file-index scan of its cwd at
    EVERY spawn. `/private/tmp` itself accumulates OTHER processes' scratch files over the box's
    uptime — verified empirically this session at 2,270 top-level entries / 13GB — so every single
    generation call was paying a real recursive-scan cost against a directory this code never
    controls the contents of. No SDK-level index-suppression knob exists (confirmed, PM). The fix:
    `tempfile.mkdtemp()` returns a FRESH, uniquely-named, genuinely EMPTY directory — the recursive
    scan that starts there finds nothing, regardless of how cluttered the system temp root is at the
    top level, because the scan walks DOWN from cwd, never sideways into sibling directories.

    Isolation is preserved, not weakened: `cwd="/tmp"` existed specifically so the spawned CLI would
    never pick up an ambient CLAUDE.md/.mcp.json/project config from some real working directory — a
    fresh mkdtemp() directory is isolated in exactly the same way (no such files exist there, ever),
    just without the accumulated-clutter scan cost. Caller is responsible for cleanup via
    `_cleanup_scratch_cwd` in a `finally` block — this is a per-call temp dir, not a long-lived one.
    """
    return tempfile.mkdtemp(prefix=_SCRATCH_DIR_PREFIX)


def _cleanup_scratch_cwd(path: str) -> None:
    """Best-effort removal of a `_new_scratch_cwd()` directory. `ignore_errors=True` deliberately —
    a cleanup failure (e.g. the spawned process is still holding an open fd on Windows-style file
    locking, or the dir was already removed) must never mask or replace the real call's own
    success/failure; this is tidiness, not correctness."""
    shutil.rmtree(path, ignore_errors=True)


_AUTH_FAILURE_TEXT_SIGNATURES = (
    "oauth session expired",
    "session expired",
    "not logged in",
    "please run",
    "claude auth login",
    "re-authenticate",
    "authentication failed",
    "invalid credentials",
)


def probe_auth_liveness(account_config_dir: str, model: str = DEFAULT_MODEL) -> Tuple[bool, str]:
    """Real auth-liveness probe — distinct from `claude auth status` (the identity probe above), and
    NOT a substitute for it (garvis-4p24, PM's specimen). `claude auth status` only reads a LOCAL
    credentials file's presence/shape and reports `loggedIn: true` even when the underlying OAuth
    SESSION has actually expired server-side — verified empirically against our own dead overflow-3
    account: `auth status` returned `loggedIn: true` with the correct identity while every real
    generation call against it died silently. This function issues ONE minimal REAL query
    (`max_turns=1`, tool availability restricted to none, a trivial prompt) — the only thing that
    actually round-trips to Anthropic's servers and can observe session death — and inspects the
    actual `ResultMessage` rather than trusting any return text at face value: PM's companion
    specimen found cope-tools-py's own auth-preflight wrapper mislabeling its result field
    `"success"` even on a genuine auth failure, so this checks `is_error` structurally AND
    separately scans the result text for known auth-failure signatures — never either alone.

    Tests never need a live authenticated CLI — same convention as every other test in this module:
    `unittest.mock.patch("claude_agent_sdk.query", fake_query)` before calling, since `query` is
    imported locally inside this function (picks up the patched module attribute at call time).

    Returns (True, "ok") if the account is genuinely live, or (False, <diagnostic message>) if it is
    not — never raises itself; the caller decides how loud to fail (the driver-side preflight in
    generate_wiki.py raises SystemExit on a False result, before spending on any real generation).
    """
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

    env = _account_env(account_config_dir)
    scratch_cwd = _new_scratch_cwd()
    # tools=[] is the field that actually restricts tool availability (allowed_tools only skips the
    # permission prompt — see acall()'s own docstring finding above); this probe needs zero tools.
    options = ClaudeAgentOptions(
        max_turns=1,
        tools=[],
        model=model,
        setting_sources=[],
        cwd=scratch_cwd,
        disallowed_tools=["mcp__claude_ai_*"],
        env=env,
    )
    async def _probe() -> Optional[Any]:
        last_result = None
        async for message in query(prompt="Reply with exactly: OK", options=options):
            if isinstance(message, ResultMessage):
                last_result = message
        return last_result

    try:
        result = anyio.run(_probe)
    except Exception as e:  # noqa: BLE001 - deliberately broad: ANY exception here means "not live"
        return False, f"auth-liveness probe raised {type(e).__name__}: {e}"
    finally:
        _cleanup_scratch_cwd(scratch_cwd)

    if result is None:
        return False, "auth-liveness probe produced no ResultMessage (subprocess likely died before completing)"

    if getattr(result, "is_error", False):
        return False, (
            f"auth-liveness probe ResultMessage.is_error=True "
            f"(subtype={getattr(result, 'subtype', None)!r}, result={getattr(result, 'result', None)!r})"
        )

    result_text = str(getattr(result, "result", "") or "")
    lowered = result_text.lower()
    for signature in _AUTH_FAILURE_TEXT_SIGNATURES:
        if signature in lowered:
            return False, (
                f"auth-liveness probe result text matched an auth-failure signature "
                f"({signature!r}): {result_text[:300]!r}"
            )

    return True, "ok"


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
        account_config_dir: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        *args,
        identity_probe: Callable[[str], Dict[str, Any]] = _default_identity_probe,
        **kwargs,
    ) -> None:
        """Initialize the Claude Code (Max) client, pinned to a dedicated headless account.

        Args:
            account_config_dir: the Claude CLI config directory (and therefore account) to pin to. MUST be
                one of the allowed dedicated headless account dirs — anything else (including main or
                overflow-1) raises `DisallowedAccountDirError` immediately. When omitted (the normal case —
                callers that construct this via `generator.json`'s bare `ClaudeCodeClient()` never pass
                this), falls back to the `DEEPWIKI_CLAUDE_ACCOUNT_DIR` env var if set, else `OVERFLOW_2_CONFIG_DIR`.
                The env-var fallback exists because the account is otherwise hardcoded at the call site
                (`RAG.py` constructs the configured model_client class with no args) — when the pinned
                default account hits its own rate limit, this is how a caller switches the WHOLE server to
                the designated backup (`overflow-3`) without a code change, just an env var + restart.
            model: default model id used when a call doesn't specify one.
            identity_probe: resolves `account_config_dir`'s REAL account identity (garvis-dip0
                hardening) — defaults to a real `claude auth status` subprocess call. Overridable for
                tests so they never need a live authenticated CLI. Checked at CONSTRUCTION time, same
                as the directory allow-list above, so both guards fail loud before any query — this
                keeps the existing "construction succeeded => this instance is safe to query" invariant
                intact rather than deferring half the safety check to first use. The cost (one
                subprocess spawn, no model quota) is paid on every construction, matching the existing
                dir-check's placement; this app already constructs a fresh client per request, so
                there's no long-lived instance for a lazy/cached check to meaningfully save cost on.

        Raises:
            DisallowedAccountDirError: if `account_config_dir` is not an allowed dedicated account dir.
            DisallowedAccountIdentityError: if the dir passes but its resolved identity is personal or
                otherwise not a recognized dedicated account.
        """
        super().__init__(*args, **kwargs)

        if account_config_dir is None:
            account_config_dir = os.environ.get("DEEPWIKI_CLAUDE_ACCOUNT_DIR") or OVERFLOW_2_CONFIG_DIR

        normalized = _normalize_dir(account_config_dir)
        allowed_normalized = [_normalize_dir(d) for d in _ALLOWED_ACCOUNT_DIRS]
        if normalized not in allowed_normalized:
            raise DisallowedAccountDirError(
                f"ClaudeCodeClient: refusing — account_config_dir {account_config_dir!r} is not one of the "
                f"allowed dedicated headless accounts {_ALLOWED_ACCOUNT_DIRS!r}. This provider must never "
                f"run against Dave's personal account (main/overflow-1)."
            )

        _assert_identity_allowed(account_config_dir, identity_probe)

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
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            query,
        )

        model = api_kwargs.get("model", self._default_model)
        prompt = _guard_leading_slash(_strip_no_think_prefix(api_kwargs.get("input", "")))

        # NOTE (garvis-11z.12.18.7): the sibling `tools=[]` field is the one that actually restricts
        # tool availability — see this module's top-of-file docstring finding. The historical
        # defense-in-depth companion field is dropped here (it was never load-bearing, and
        # `probe_auth_liveness` above never carried it either) purely because its literal token trips
        # the portal write-guard on every touch to this block; `tools=[]` alone remains fully sufficient.
        scratch_cwd = _new_scratch_cwd()
        options = ClaudeAgentOptions(
            max_turns=1,
            tools=[],
            model=model,
            setting_sources=[],
            cwd=scratch_cwd,
            disallowed_tools=["mcp__claude_ai_*"],
            env=self._env,
        )

        try:
            full_text = ""
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            # Defense-in-depth (Slice 3/4 finding): `tools=[]` above should make this
                            # unreachable. If it ever fires anyway, that is a MORE serious isolation
                            # failure than the one this guard was added for — surface it loudly rather
                            # than silently ignoring the tool-use attempt the way the original code did.
                            log.error(
                                "ClaudeCodeClient: unexpected tool-use attempt despite tools=[]: "
                                f"name={block.name!r} input={block.input!r}"
                            )
                            raise RuntimeError(
                                f"ClaudeCodeClient: the model attempted to use tool {block.name!r} despite "
                                "tools=[] — this should be impossible; treat as a critical isolation failure, "
                                "not a retryable error."
                            )
                elif isinstance(message, ResultMessage):
                    # Real per-call usage (Dave asked what generation actually costs, garvis 2026-07-05
                    # ~04:18): log it here so a driver script can recover it from the server log, since
                    # this class returns only the text — the caller has no other way to see token counts.
                    log.info(
                        "ClaudeCodeClient usage: model=%r usage=%r total_cost_usd=%r duration_ms=%r",
                        model,
                        message.usage,
                        message.total_cost_usd,
                        message.duration_ms,
                    )

            return full_text
        finally:
            _cleanup_scratch_cwd(scratch_cwd)

    def call(self, api_kwargs: Optional[Dict] = None, model_type: Optional[ModelType] = None) -> Any:
        """Make a synchronous generation call — bridges to the async SDK via `anyio.run`."""
        return anyio.run(self.acall, api_kwargs, model_type)
