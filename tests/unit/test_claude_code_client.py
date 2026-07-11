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
    probe_auth_liveness,
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


# --- DEEPWIKI_CLAUDE_ACCOUNT_DIR env-var fallback (backup-account switch without a code change) ---


def test_omitted_account_config_dir_defaults_to_overflow_2_when_env_unset(monkeypatch):
    monkeypatch.delenv("DEEPWIKI_CLAUDE_ACCOUNT_DIR", raising=False)
    client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
    assert client._account_config_dir == OVERFLOW_2_CONFIG_DIR


def test_omitted_account_config_dir_honors_env_var_override(monkeypatch):
    monkeypatch.setenv("DEEPWIKI_CLAUDE_ACCOUNT_DIR", OVERFLOW_3_CONFIG_DIR)
    client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
    assert client._account_config_dir == OVERFLOW_3_CONFIG_DIR


def test_explicit_account_config_dir_wins_over_env_var(monkeypatch):
    """An explicitly-passed account_config_dir must always take priority over the env-var fallback —
    the env var only fills in when the caller passes nothing at all."""
    monkeypatch.setenv("DEEPWIKI_CLAUDE_ACCOUNT_DIR", OVERFLOW_3_CONFIG_DIR)
    client = ClaudeCodeClient(account_config_dir=OVERFLOW_2_CONFIG_DIR, identity_probe=_FAKE_ALLOWED_PROBE)
    assert client._account_config_dir == OVERFLOW_2_CONFIG_DIR


def test_env_var_pointing_at_a_disallowed_dir_still_refuses():
    """The env-var fallback does not bypass the allow-list — a misconfigured env var pointing at main
    must still refuse loudly, exactly like an explicit bad account_config_dir would."""
    import os

    old = os.environ.get("DEEPWIKI_CLAUDE_ACCOUNT_DIR")
    os.environ["DEEPWIKI_CLAUDE_ACCOUNT_DIR"] = "/Users/dwillner/.claude"
    try:
        with pytest.raises(DisallowedAccountDirError):
            ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
    finally:
        if old is None:
            os.environ.pop("DEEPWIKI_CLAUDE_ACCOUNT_DIR", None)
        else:
            os.environ["DEEPWIKI_CLAUDE_ACCOUNT_DIR"] = old


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


@pytest.mark.asyncio
async def test_acall_logs_result_message_usage_stats(caplog):
    """Real per-call token/cost usage (Dave asked what generation actually costs) must be logged
    from the SDK's ResultMessage — the only place this class ever sees it, since acall() itself
    only returns the generated text."""
    import logging as _logging
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

    async def fake_query(*, prompt, options):
        yield AssistantMessage(model="claude-sonnet-4-6", content=[TextBlock(text="hi")])
        yield ResultMessage(
            subtype="success",
            duration_ms=500,
            duration_api_ms=400,
            is_error=False,
            num_turns=1,
            session_id="s1",
            total_cost_usd=0.01,
            usage={"input_tokens": 123, "output_tokens": 45},
        )

    with caplog.at_level(_logging.INFO, logger="api.claude_code_client"):
        with patch("claude_agent_sdk.query", fake_query):
            client = ClaudeCodeClient(identity_probe=_FAKE_ALLOWED_PROBE)
            await client.acall(
                api_kwargs={"model": "claude-sonnet-4-6", "input": "hello"}, model_type=ModelType.LLM
            )

    usage_logs = [r.getMessage() for r in caplog.records if "usage" in r.getMessage().lower()]
    assert usage_logs, "expected a logged line containing the ResultMessage usage stats"
    assert "123" in usage_logs[0] and "45" in usage_logs[0]


# --- garvis-4p24: probe_auth_liveness — a REAL liveness check, distinct from `claude auth status` ---
# (PM's specimen: `claude auth status` returns loggedIn:true for a session that has actually expired
# server-side; only a real round-trip query can observe the difference. Verified empirically against
# our own dead overflow-3 account this same session.)


def test_probe_auth_liveness_returns_true_on_a_genuinely_live_account():
    from claude_agent_sdk import ResultMessage

    async def fake_query(*, prompt, options):
        yield ResultMessage(
            subtype="success", duration_ms=500, duration_api_ms=400, is_error=False, num_turns=1,
            session_id="s1", total_cost_usd=0.0001, result="OK",
        )

    with patch("claude_agent_sdk.query", fake_query):
        live, detail = probe_auth_liveness(OVERFLOW_3_CONFIG_DIR)
    assert live is True
    assert detail == "ok"


def test_probe_auth_liveness_returns_false_when_result_message_is_error():
    """The structural check — never trust return TEXT alone (garvis-4p24's second finding: an auth
    wrapper can mislabel its own text field 'success' even on genuine failure)."""
    from claude_agent_sdk import ResultMessage

    async def fake_query(*, prompt, options):
        yield ResultMessage(
            subtype="error_during_execution", duration_ms=100, duration_api_ms=50, is_error=True,
            num_turns=0, session_id="s1", total_cost_usd=0.0, result="success",
        )

    with patch("claude_agent_sdk.query", fake_query):
        live, detail = probe_auth_liveness(OVERFLOW_3_CONFIG_DIR)
    assert live is False
    assert "is_error=True" in detail


def test_probe_auth_liveness_returns_false_on_an_auth_failure_text_signature():
    """The textual check — catches an auth failure surfaced only as prose in a non-error result,
    the exact 'raw CLI says OAuth session expired' case PM's specimen names."""
    from claude_agent_sdk import ResultMessage

    async def fake_query(*, prompt, options):
        yield ResultMessage(
            subtype="success", duration_ms=100, duration_api_ms=50, is_error=False, num_turns=1,
            session_id="s1", total_cost_usd=0.0, result="Error: OAuth session expired, please re-authenticate.",
        )

    with patch("claude_agent_sdk.query", fake_query):
        live, detail = probe_auth_liveness(OVERFLOW_3_CONFIG_DIR)
    assert live is False
    assert "oauth session expired" in detail.lower()


def test_probe_auth_liveness_returns_false_when_the_probe_raises():
    async def fake_query(*, prompt, options):
        raise RuntimeError("subprocess spawn failed")
        yield  # pragma: no cover — makes this an async generator; never actually reached.

    with patch("claude_agent_sdk.query", fake_query):
        live, detail = probe_auth_liveness(OVERFLOW_3_CONFIG_DIR)
    assert live is False
    assert "RuntimeError" in detail


def test_probe_auth_liveness_returns_false_when_no_result_message_ever_arrives():
    """Matches the actual observed symptom this specimen was built from: the process died silently
    mid-subprocess-spawn, producing no ResultMessage at all — not an exception, not an error result,
    just nothing."""

    async def fake_query(*, prompt, options):
        return
        yield  # pragma: no cover — makes this an async generator; never actually reached.

    with patch("claude_agent_sdk.query", fake_query):
        live, detail = probe_auth_liveness(OVERFLOW_3_CONFIG_DIR)
    assert live is False
    assert "no ResultMessage" in detail


def test_probe_auth_liveness_uses_the_pinned_accounts_env():
    """The probe must build its env from the SAME account-pin-and-blank recipe as real generation
    calls — not the ambient environment — else it could report a different account's liveness."""
    captured = {}

    async def fake_query(*, prompt, options):
        captured["options"] = options
        yield_from_nothing = None  # noqa: F841
        return
        yield  # pragma: no cover — makes this an async generator; never actually reached.

    with patch("claude_agent_sdk.query", fake_query):
        probe_auth_liveness(OVERFLOW_3_CONFIG_DIR)

    options = captured["options"]
    assert options.env["CLAUDE_CONFIG_DIR"] == OVERFLOW_3_CONFIG_DIR
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert options.env["ANTHROPIC_API_KEY"] == ""
    assert options.tools == [], "the probe must also run with zero tool availability, same as real generation"
