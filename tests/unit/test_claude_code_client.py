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
    OVERFLOW_2_CONFIG_DIR,
    OVERFLOW_3_CONFIG_DIR,
    _guard_leading_slash,
)


def test_fail_closed_guard_rejects_main():
    with pytest.raises(DisallowedAccountDirError):
        ClaudeCodeClient(account_config_dir="/Users/dwillner/.claude")


def test_fail_closed_guard_rejects_overflow_1():
    with pytest.raises(DisallowedAccountDirError):
        ClaudeCodeClient(account_config_dir="/Users/dwillner/.claude-overflow")


def test_fail_closed_guard_allows_overflow_2_default():
    client = ClaudeCodeClient()
    assert client._account_config_dir == OVERFLOW_2_CONFIG_DIR
    assert client._env["CLAUDE_CONFIG_DIR"] == OVERFLOW_2_CONFIG_DIR


def test_fail_closed_guard_allows_overflow_3():
    client = ClaudeCodeClient(account_config_dir=OVERFLOW_3_CONFIG_DIR)
    assert client._account_config_dir == OVERFLOW_3_CONFIG_DIR


def test_env_blanks_ambient_token_and_key():
    """The env-merge trap fix: both must be blanked, not just one, else an ambient value would win
    ClaudeAgentOptions.env's merge-onto-os.environ precedence."""
    client = ClaudeCodeClient()
    assert client._env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert client._env["ANTHROPIC_API_KEY"] == ""
    assert client._env["CLAUDE_SECURESTORAGE_CONFIG_DIR"] == ""


def test_convert_inputs_llm():
    client = ClaudeCodeClient()
    api_kwargs = client.convert_inputs_to_api_kwargs(
        input="hello", model_kwargs={"model": "claude-sonnet-4-6"}, model_type=ModelType.LLM
    )
    assert api_kwargs == {"model": "claude-sonnet-4-6", "input": "hello"}


def test_convert_inputs_llm_defaults_model():
    client = ClaudeCodeClient(model="claude-haiku-4-5")
    api_kwargs = client.convert_inputs_to_api_kwargs(input="hi", model_kwargs={}, model_type=ModelType.LLM)
    assert api_kwargs["model"] == "claude-haiku-4-5"


def test_convert_inputs_embedder_not_implemented():
    client = ClaudeCodeClient()
    with pytest.raises(NotImplementedError):
        client.convert_inputs_to_api_kwargs(input="hello", model_kwargs={}, model_type=ModelType.EMBEDDER)


def test_guard_leading_slash_defuses_no_think_prefix():
    """The exact real-world artifact this guard exists for: this app's universal prompt prefix."""
    guarded = _guard_leading_slash("/no_think You are a helpful assistant.\n\n")
    assert guarded == " /no_think You are a helpful assistant.\n\n"
    assert not guarded.startswith("/")


def test_guard_leading_slash_passthrough_for_normal_prompts():
    assert _guard_leading_slash("Explain this repository.") == "Explain this repository."


def test_guard_leading_slash_passthrough_for_empty_string():
    assert _guard_leading_slash("") == ""


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
        client = ClaudeCodeClient()
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
        client = ClaudeCodeClient()
        with pytest.raises(RuntimeError, match="tool.*Bash"):
            await client.acall(
                api_kwargs={"model": "claude-sonnet-4-6", "input": "hello"}, model_type=ModelType.LLM
            )
