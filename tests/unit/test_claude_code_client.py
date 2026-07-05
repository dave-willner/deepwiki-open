"""Hermetic unit tests for ClaudeCodeClient's pure/deterministic logic — no network, no SDK subprocess call.

Covers: the account-pin fail-closed guard (the Dave-direct safety requirement), the
convert_inputs_to_api_kwargs contract, and the leading-slash CLI-command guard (a real footgun found
empirically during Slice 2 end-to-end testing: a prompt starting with "/" — e.g. this app's own universal
"/no_think {system_prompt}" prefix — gets parsed as a `claude` CLI slash command instead of prompt text).
"""

import sys
from pathlib import Path

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
