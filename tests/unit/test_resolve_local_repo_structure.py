"""Hermetic unit tests for resolve_local_repo_structure (garvis-11z.17).

/local_repo/structure previously had NO exclusion filtering at all — just a hardcoded
hidden-dirs/__pycache__/node_modules/.venv filter baked into the endpoint's own os.walk, no way for
a caller to add more. On a repo with huge non-source scratch directories (e.g. mutation-testing
output dirs, ~194MB each) that floods the structure-determination prompt fed to the LLM. This tests
the extracted, reusable fix directly (no FastAPI, no TestClient, no network) — mirroring the existing
convention set by test_get_local_files_context.py / test_clean_directory_token.py.
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.data_pipeline import resolve_local_repo_structure  # noqa: E402


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_default_behavior_is_unchanged_for_callers_passing_no_params(tmp_path):
    # Same baseline the endpoint always had: hidden dirs, __pycache__, node_modules, .venv excluded.
    _write(tmp_path / "src" / "main.py")
    _write(tmp_path / ".git" / "HEAD")
    _write(tmp_path / "__pycache__" / "main.cpython-312.pyc")
    _write(tmp_path / "node_modules" / "pkg" / "index.js")
    _write(tmp_path / ".venv" / "lib" / "site.py")
    _write(tmp_path / "README.md", "# Hello\n")

    file_tree_str, readme = resolve_local_repo_structure(str(tmp_path))
    lines = set(file_tree_str.splitlines())

    assert os.path.join("src", "main.py") in lines
    assert "README.md" in lines
    assert readme == "# Hello\n"
    assert not any(".git" in line for line in lines)
    assert not any("__pycache__" in line for line in lines)
    assert not any("node_modules" in line for line in lines)
    assert not any(".venv" in line for line in lines)


def test_excluded_dirs_prunes_a_caller_supplied_scratch_dir_not_in_the_baseline(tmp_path):
    # The actual bug this bead names: mutation-testing scratch dirs aren't in ANY hardcoded default
    # (baseline or DEFAULT_EXCLUDED_DIRS), so without excluded_dirs support they flood the tree.
    _write(tmp_path / "src" / "main.py")
    _write(tmp_path / "mutants" / "main.py.orig")
    _write(tmp_path / "mutants.gate-aside-1783378187" / "main.py.orig")

    file_tree_str, _ = resolve_local_repo_structure(
        str(tmp_path), excluded_dirs=["./mutants/", "./mutants.gate-aside-1783378187/"]
    )
    lines = set(file_tree_str.splitlines())

    assert os.path.join("src", "main.py") in lines
    assert not any("mutants" in line for line in lines)


def test_excluded_dirs_uses_clean_directory_token_not_naive_strip(tmp_path):
    # Regression guard for the exact bug _clean_directory_token was built to fix (garvis-9khs): a
    # naive str.strip('./') on './.garvis/' collapses to 'garvis', which would then spuriously
    # match an ancestor path component literally named 'garvis' and silently exclude everything.
    _write(tmp_path / "garvis" / "real_project_file.py")  # a dir literally named "garvis"
    _write(tmp_path / ".garvis" / "scratch.json")  # the actual dotted dir meant to be excluded

    file_tree_str, _ = resolve_local_repo_structure(str(tmp_path), excluded_dirs=["./.garvis/"])
    lines = set(file_tree_str.splitlines())

    assert os.path.join("garvis", "real_project_file.py") in lines, (
        "excluding './.garvis/' must not spuriously exclude an unrelated dir named 'garvis'"
    )
    assert not any(line.startswith(".garvis" + os.sep) for line in lines)


def test_included_dirs_switches_to_inclusion_mode_and_drops_default_baseline_exclusion(tmp_path):
    _write(tmp_path / "src" / "keep.py")
    _write(tmp_path / "other" / "skip.py")
    _write(tmp_path / ".venv" / "lib" / "site.py")  # would be excluded by default, irrelevant here

    file_tree_str, _ = resolve_local_repo_structure(str(tmp_path), included_dirs=["src"])
    lines = set(file_tree_str.splitlines())

    assert os.path.join("src", "keep.py") in lines
    assert os.path.join("other", "skip.py") not in lines
    assert not any(".venv" in line for line in lines)


def test_included_dirs_matches_a_nested_ancestor_not_just_the_immediate_directory_name(tmp_path):
    # The bug an early-pruning-by-immediate-name implementation would have: included_dirs=["clr"]
    # must still surface src/cope_tools/clr/relabel.py even though "src" and "cope_tools" (the
    # ancestors actually walked through) never match "clr" themselves.
    _write(tmp_path / "src" / "cope_tools" / "clr" / "relabel.py")
    _write(tmp_path / "src" / "cope_tools" / "pareto" / "optimize.py")

    file_tree_str, _ = resolve_local_repo_structure(str(tmp_path), included_dirs=["clr"])
    lines = set(file_tree_str.splitlines())

    assert os.path.join("src", "cope_tools", "clr", "relabel.py") in lines
    assert os.path.join("src", "cope_tools", "pareto", "optimize.py") not in lines


def test_excluded_dirs_supports_a_nested_compound_path_token(tmp_path):
    # garvis-ownx gate finding: _clean_directory_token only strips './' and trailing '/', never
    # splits on internal '/' — so './api/logs/' cleaned down to the single string 'api/logs', but
    # dir_pruning_allowed was called once per BARE directory name during the walk ('api', then
    # separately 'logs'), neither of which ever equalled the compound token 'api/logs'. A nested
    # exclusion path silently never matched. Also proves the fix is EXACT, not overreaching: a
    # same-named 'logs' dir living somewhere else in the tree must survive.
    _write(tmp_path / "api" / "main.py")
    _write(tmp_path / "api" / "logs" / "application.log")
    _write(tmp_path / "other" / "logs" / "keep.log")

    file_tree_str, _ = resolve_local_repo_structure(str(tmp_path), excluded_dirs=["./api/logs/"])
    lines = set(file_tree_str.splitlines())

    assert os.path.join("api", "main.py") in lines
    assert not any(line.startswith(os.path.join("api", "logs")) for line in lines), (
        "excluding './api/logs/' must prune the nested api/logs directory"
    )
    assert os.path.join("other", "logs", "keep.log") in lines, (
        "excluding './api/logs/' must NOT spuriously prune an unrelated dir elsewhere named 'logs'"
    )


def test_readme_is_still_found_case_insensitively(tmp_path):
    _write(tmp_path / "sub" / "Readme.md", "# Sub\n")
    file_tree_str, readme = resolve_local_repo_structure(str(tmp_path))
    assert readme == "# Sub\n"


def test_hidden_and_dunder_init_and_ds_store_files_stay_excluded_in_both_modes(tmp_path):
    _write(tmp_path / "src" / "__init__.py")
    _write(tmp_path / "src" / ".DS_Store")
    _write(tmp_path / "src" / ".hidden")
    _write(tmp_path / "src" / "real.py")

    excl_tree, _ = resolve_local_repo_structure(str(tmp_path))
    incl_tree, _ = resolve_local_repo_structure(str(tmp_path), included_dirs=["src"])

    for file_tree_str in (excl_tree, incl_tree):
        lines = set(file_tree_str.splitlines())
        assert os.path.join("src", "real.py") in lines
        assert os.path.join("src", "__init__.py") not in lines
        assert os.path.join("src", ".DS_Store") not in lines
        assert os.path.join("src", ".hidden") not in lines
