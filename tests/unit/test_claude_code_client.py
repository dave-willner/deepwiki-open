"""Hermetic unit tests for ClaudeCodeClient's pure/deterministic logic — no network, no SDK subprocess call.

Covers: the account-pin fail-closed guard (the Dave-direct safety requirement), the
convert_inputs_to_api_kwargs contract, the leading-slash CLI-command guard (a real footgun found
empirically during Slice 2 end-to-end testing: a prompt starting with "/" — e.g. this app's own universal
"/no_think {system_prompt}" prefix — gets parsed as a `claude` CLI slash command instead of prompt text),
and the tool-isolation contract (a real footgun found empirically during Slice 3/4 testing: `allowed_tools=[]`
alone does NOT disable built-in tools — only `tools=[]` does; without it a long/complex prompt provoked the
model into actually executing Bash and exploring the filesystem).
"""

import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from adalflow.core.types import ModelType

from api.claude_code_client import (
    ClaudeCodeClient,
    DisallowedAccountDirError,
    DisallowedAccountIdentityError,
    OVERFLOW_2_CONFIG_DIR,
    OVERFLOW_3_CONFIG_DIR,
    _guard_leading_slash,
    _strip_no_think_prefix,
)

# A fake identity probe standing in for a real `claude auth status` subprocess call, so every test
# in this file stays hermetic (no live CLI/auth dependency) except the dedicated identity-guard
# tests below, which exercise the refusal logic directly with their own fake probes.
_FAKE_ALLOWED_PROBE = lambda account_config_dir: {"email": "claude-max-02@zentropi.ai"}  # noqa: E731


def test_fail_closed_guard_rejects_main():
    with pytest.raises(DisallowedAccountDirError):
        ClaudeCodeClient(account_config_dir="/Users/dwillner/.claude", identity_probe=_FAKE_ALLOWED_PROBE)


def test_fail_closed_guard_rejects_overflow_1():
    with pytest.raises(DisallowedAccountDirError):
        ClaudeCodeClient(account_config_dir="/Users/dwillner/.claude-overflow", identity_probe=_FAKE_ALLOWED_PROBE)


def test_fail_closed_guard_rejects_main_without_ever_probing_identity():
    """The cheap dir-allowlist check must run BEFORE the identity probe — a disallowed dir refuses
    immediately without paying for a subprocess call at all."""
    probe_calls = []

    def spy_probe(account_config_dir):
        probe_calls.append(account_config_dir)
        return {"email": "claude-max-02@zentropi.ai"}

    with pytest.raises(DisallowedAccountDirError):
        ClaudeCodeClient(account_config_dir="/Users/dwillner/.claude", identity_probe=spy_probe)
    assert probe_calls == [], "the identity probe must never be called when the dir check already refused"


def test_fail_closed_guard_allows_overflow_2_default():
    client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
    assert client._account_config_dir == OVERFLOW_2_CONFIG_DIR
    assert client._env["CLAUDE_CONFIG_DIR"] == OVERFLOW_2_CONFIG_DIR


def test_fail_closed_guard_allows_overflow_3():
    client = ClaudeCodeClient(account_config_dir=OVERFLOW_3_CONFIG_DIR, identity_probe=_FAKE_ALLOWED_PROBE)
    assert client._account_config_dir == OVERFLOW_3_CONFIG_DIR


def test_env_blanks_ambient_token_and_key():
    """The env-merge trap fix: both must be blanked, not just one, else an ambient value would win
    ClaudeAgentOptions.env's merge-onto-os.environ precedence."""
    client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
    assert client._env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert client._env["ANTHROPIC_API_KEY"] == ""
    assert client._env["CLAUDE_SECURESTORAGE_CONFIG_DIR"] == ""


def test_convert_inputs_llm():
    client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
    api_kwargs = client.convert_inputs_to_api_kwargs(
        input="hello", model_kwargs={"model": "claude-sonnet-4-6"}, model_type=ModelType.LLM
    )
    assert api_kwargs == {"model": "claude-sonnet-4-6", "input": "hello"}


def test_convert_inputs_llm_defaults_model():
    client = ClaudeCodeClient(model="claude-haiku-4-5", identity_probe=_FAKE_ALLOWED_PROBE)
    api_kwargs = client.convert_inputs_to_api_kwargs(input="hi", model_kwargs={}, model_type=ModelType.LLM)
    assert api_kwargs["model"] == "claude-haiku-4-5"


def test_convert_inputs_embedder_not_implemented():
    client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
    with pytest.raises(NotImplementedError):
        client.convert_inputs_to_api_kwargs(input="hello", model_kwargs={}, model_type=ModelType.EMBEDDER)


# --- garvis-dip0: identity-denylist guard (hardening beyond the directory allow-list) ---


def test_identity_guard_allows_dedicated_max_account():
    client = ClaudeCodeClient(identity_probe=lambda d: {"email": "claude-max-02@zentropi.ai"})
    assert client._account_config_dir == OVERFLOW_2_CONFIG_DIR


def test_identity_guard_allows_a_different_dedicated_max_account_number():
    """The positive pattern is claude-max-N@zentropi.ai for ANY N — not hardcoded to -02/-03, so a
    future re-numbered or additional dedicated account is accepted without a code change."""
    client = ClaudeCodeClient(identity_probe=lambda d: {"email": "claude-max-07@zentropi.ai"})
    assert client._account_config_dir == OVERFLOW_2_CONFIG_DIR


def test_identity_guard_refuses_denylisted_personal_gmail():
    with pytest.raises(DisallowedAccountIdentityError):
        ClaudeCodeClient(identity_probe=lambda d: {"email": "dave.willner@gmail.com"})


def test_identity_guard_refuses_denylisted_personal_zentropi():
    with pytest.raises(DisallowedAccountIdentityError):
        ClaudeCodeClient(identity_probe=lambda d: {"email": "dave@zentropi.ai"})


def test_identity_guard_refuses_identity_not_matching_dedicated_pattern():
    """Defense-in-depth beyond the explicit denylist: an identity that ISN'T on the denylist but also
    isn't a recognized dedicated-account shape must still be refused — the allow-list is a positive
    pattern, not just an exclusion of two known personal addresses."""
    with pytest.raises(DisallowedAccountIdentityError):
        ClaudeCodeClient(identity_probe=lambda d: {"email": "some-other-account@zentropi.ai"})


def test_identity_guard_refuses_when_probe_reports_not_logged_in():
    with pytest.raises(DisallowedAccountIdentityError):
        ClaudeCodeClient(identity_probe=lambda d: {"loggedIn": False, "email": ""})


def test_identity_guard_receives_the_account_config_dir_under_test():
    seen = {}

    def probe(account_config_dir):
        seen["dir"] = account_config_dir
        return {"email": "claude-max-03@zentropi.ai"}

    ClaudeCodeClient(account_config_dir=OVERFLOW_3_CONFIG_DIR, identity_probe=probe)
    assert seen["dir"] == OVERFLOW_3_CONFIG_DIR


def test_guard_leading_slash_defuses_no_think_prefix():
    """The exact real-world artifact this guard exists for: this app's universal prompt prefix."""
    guarded = _guard_leading_slash("/no_think You are a helpful assistant.\n\n")
    assert guarded == " /no_think You are a helpful assistant.\n\n"
    assert not guarded.startswith("/")


def test_guard_leading_slash_passthrough_for_normal_prompts():
    assert _guard_leading_slash("Explain this repository.") == "Explain this repository."


def test_guard_leading_slash_passthrough_for_empty_string():
    assert _guard_leading_slash("") == ""


# --- garvis-ulki: strip the Qwen /no_think prefix instead of space-guarding it ---


def test_strip_no_think_prefix_removes_the_exact_artifact():
    """This app prepends `f"/no_think {system_prompt}"` to EVERY provider's prompt (a Qwen/Ollama
    thinking-mode suppression directive, meaningless to Claude). Stripping it outright means no
    noise-prefix reaches the model at all — cleaner than defusing it with a leading space."""
    stripped = _strip_no_think_prefix("/no_think You are a helpful assistant.\n\n")
    assert stripped == "You are a helpful assistant.\n\n"
    assert "no_think" not in stripped


def test_strip_no_think_prefix_passthrough_when_absent():
    assert _strip_no_think_prefix("Explain this repository.") == "Explain this repository."


def test_strip_no_think_prefix_passthrough_for_empty_string():
    assert _strip_no_think_prefix("") == ""


def test_strip_no_think_prefix_does_not_touch_a_similarly_named_but_different_command():
    """Only the EXACT literal artifact ("/no_think " with its trailing space, matching exactly how
    this app always constructs it) is stripped — a different, unrelated leading slash-word is left
    alone for `_guard_leading_slash` to handle as the general backstop."""
    prompt = "/no_thinking_about_it, let's go"
    assert _strip_no_think_prefix(prompt) == prompt


def test_acall_strips_no_think_prefix_before_reaching_the_sdk():
    """Integration-ish: the actual prompt handed to `query()` must contain no "/no_think" artifact
    at all — not just be defused with a leading space."""
    import asyncio

    captured = {}

    async def fake_query(*, prompt, options):
        captured["prompt"] = prompt
        return
        yield  # pragma: no cover

    async def run():
        with patch("claude_agent_sdk.query", fake_query):
            client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
            await client.acall(
                api_kwargs={"model": "claude-sonnet-4-6", "input": "/no_think You are helpful.\n\n<query>hi</query>"},
                model_type=ModelType.LLM,
            )

    asyncio.run(run())
    assert "no_think" not in captured["prompt"]
    assert captured["prompt"] == "You are helpful.\n\n<query>hi</query>"


def test_acall_still_guards_other_leading_slashes_as_a_backstop():
    """`_guard_leading_slash` remains the general backstop for any OTHER leading-slash prompt this
    app might ever construct — only the specific /no_think artifact is stripped outright."""
    import asyncio

    captured = {}

    async def fake_query(*, prompt, options):
        captured["prompt"] = prompt
        return
        yield  # pragma: no cover

    async def run():
        with patch("claude_agent_sdk.query", fake_query):
            client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
            await client.acall(
                api_kwargs={"model": "claude-sonnet-4-6", "input": "/some-other-command text"},
                model_type=ModelType.LLM,
            )

    asyncio.run(run())
    assert captured["prompt"] == " /some-other-command text"


@pytest.mark.asyncio
async def test_acall_sets_tools_empty_not_just_allowed_tools():
    """The load-bearing tool-isolation regression test: `tools=[]` must be passed to
    ClaudeAgentOptions, not just `allowed_tools=[]` (which does NOT disable built-in tools — see the
    SDK's own docstring: "To restrict which tools are available AT ALL, use `tools` instead."). Mocks
    the SDK's `query()` to capture the ClaudeAgentOptions actually constructed, without any real
    subprocess/network call."""
    captured_options = {}

    async def fake_query(*, prompt, options):
        captured_options["options"] = options
        return
        yield  # pragma: no cover — makes this an async generator; never actually reached.

    with patch("claude_agent_sdk.query", fake_query):
        client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
        await client.acall(
            api_kwargs={"model": "claude-sonnet-4-6", "input": "hello"}, model_type=ModelType.LLM
        )

    options = captured_options["options"]
    assert options.tools == [], "tools=[] must be set — this is what actually disables built-in tools"
    assert options.allowed_tools == []


@pytest.mark.asyncio
async def test_acall_raises_loudly_if_a_tool_use_ever_slips_through():
    """Defense-in-depth: if `ToolUseBlock` ever appears in the stream despite `tools=[]`, `acall()`
    must raise immediately rather than silently ignore it (the original code silently discarded any
    non-TextBlock content, which is exactly how the real Bash-execution incident went undetected)."""
    from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock

    async def fake_query_with_tool_use(*, prompt, options):
        yield AssistantMessage(
            model="claude-sonnet-4-6",
            content=[
                TextBlock(text="some text"),
                ToolUseBlock(id="toolu_fake", name="Bash", input={"command": "ls"}),
            ],
        )

    with patch("claude_agent_sdk.query", fake_query_with_tool_use):
        client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
        with pytest.raises(RuntimeError, match="tool.*Bash"):
            await client.acall(
                api_kwargs={"model": "claude-sonnet-4-6", "input": "hello"}, model_type=ModelType.LLM
            )
