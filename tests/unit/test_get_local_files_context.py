"""Hermetic unit tests for get_local_files_context — no network, no DB, no embedder.

Covers the retrieval-starvation fix (garvis-6vlo, slice 4): wiki-page generation for a LOCAL repo
knows the exact `relevant_files` list from the wiki-structure step, so instead of relying on FAISS
semantic retrieval over a huge, largely page-invariant instructional prompt (which was proven,
empirically, to starve pages spanning many files — the retrieval query was dominated by boilerplate
shared across all pages, so the top-k=20 chunks barely varied by page), we read those exact files'
full content directly off disk. This is deterministic: no similarity search, no top_k truncation
guesswork, no risk of picking generically-similar-but-wrong chunks.
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.data_pipeline import get_local_files_context  # noqa: E402


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_reads_full_content_of_each_listed_file(tmp_path):
    _write(tmp_path / "a.js", "const a = 1;\n")
    _write(tmp_path / "core" / "b.js", "const b = 2;\n")

    context_text, included, skipped = get_local_files_context(
        str(tmp_path), ["a.js", "core/b.js"]
    )

    assert included == ["a.js", "core/b.js"]
    assert skipped == []
    assert "## File Path: a.js" in context_text
    assert "const a = 1;" in context_text
    assert "## File Path: core/b.js" in context_text
    assert "const b = 2;" in context_text


def test_missing_file_is_skipped_not_fatal(tmp_path):
    _write(tmp_path / "a.js", "const a = 1;\n")

    context_text, included, skipped = get_local_files_context(
        str(tmp_path), ["a.js", "does/not/exist.js"]
    )

    assert included == ["a.js"]
    assert len(skipped) == 1
    assert "does/not/exist.js" in skipped[0]
    assert "not found" in skipped[0]


def test_path_traversal_outside_repo_root_is_refused(tmp_path):
    # A relevant_files entry that tries to escape the repo root (e.g. a malformed/hostile path
    # from an upstream LLM-produced file list) must never read files outside the repo.
    outside = tmp_path.parent / "outside-secret.txt"
    _write(outside, "should never be read")
    _write(tmp_path / "a.js", "const a = 1;\n")

    context_text, included, skipped = get_local_files_context(
        str(tmp_path), ["a.js", "../outside-secret.txt"]
    )

    assert included == ["a.js"]
    assert len(skipped) == 1
    assert "outside repo root" in skipped[0]
    assert "should never be read" not in context_text


def test_empty_file_list_returns_empty_context(tmp_path):
    context_text, included, skipped = get_local_files_context(str(tmp_path), [])
    assert context_text == ""
    assert included == []
    assert skipped == []


def test_budget_exhaustion_truncates_and_reports_skips(tmp_path):
    _write(tmp_path / "big1.js", "A" * 100)
    _write(tmp_path / "big2.js", "B" * 100)
    _write(tmp_path / "big3.js", "C" * 100)

    context_text, included, skipped = get_local_files_context(
        str(tmp_path), ["big1.js", "big2.js", "big3.js"], max_total_chars=150
    )

    # First file fits whole; something must give on the second; third has no budget left at all.
    assert "big1.js" in included
    assert "big3.js" not in included
    assert any("budget exhausted" in s for s in skipped)


def test_directory_entry_is_skipped_not_fatal(tmp_path):
    _write(tmp_path / "a.js", "const a = 1;\n")
    (tmp_path / "core").mkdir()

    context_text, included, skipped = get_local_files_context(
        str(tmp_path), ["a.js", "core"]
    )

    assert included == ["a.js"]
    assert len(skipped) == 1
    assert "core" in skipped[0]
