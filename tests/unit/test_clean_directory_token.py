"""Hermetic unit test for the directory-token cleaning bug found live during garvis-9khs.

`should_process_file` (nested in `read_all_documents`) used `raw.strip("./").rstrip("/")` to turn a
config entry like `"./.venv/"` into a bare path-component name (`"venv"`... except it doesn't: `str.strip`
strips a CHARACTER SET from both ends, not a literal prefix/suffix. `"./.garvis/".strip("./")` keeps
eating '.' and '/' characters past the leading dot, collapsing all the way to `"garvis"` — which then
spuriously matches ANY ancestor path component literally named `garvis` (e.g. every repository living
under a vault directory `.../garvis/projects/<repo>/...`), silently excluding every single file in the
repository. Reproduced live: `read_all_documents("/Users/dwillner/garvis/projects/cope-tools-py",
excluded_dirs=["./.garvis/", ...])` returned 0 documents (should return hundreds) because
`"./.garvis/".strip("./")` produced `"garvis"`, which is a real path component of the vault root
every project lives under.

Fix: `_clean_directory_token` uses literal `removeprefix`/`removesuffix`-equivalent trimming (only
ever strips the exact substrings `"./"` and `"/"`, never individual characters), so `"./.garvis/"` ->
`".garvis"` (correct) and `"garvis"` (the vault-root component) is never touched.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.data_pipeline import _clean_directory_token  # noqa: E402


def test_dotted_directory_name_is_not_collapsed_past_its_own_leading_dot():
    # The exact bug: './.garvis/' must clean to '.garvis', NOT 'garvis' (which would spuriously
    # match an ancestor path component of the same name).
    assert _clean_directory_token("./.garvis/") == ".garvis"


def test_ordinary_directory_name_still_cleans_correctly():
    assert _clean_directory_token("./build/") == "build"
    assert _clean_directory_token("./.venv/") == ".venv"
    assert _clean_directory_token("./mutants.gate-aside-123/") == "mutants.gate-aside-123"


def test_no_leading_dot_slash_is_a_no_op_prefix_strip():
    assert _clean_directory_token("build/") == "build"
    assert _clean_directory_token("build") == "build"


def test_trailing_slash_is_optional():
    assert _clean_directory_token("./.ruff_cache") == ".ruff_cache"
    assert _clean_directory_token("./.ruff_cache/") == ".ruff_cache"


def test_double_dot_style_scratch_dir_names_survive_intact():
    # These are real mutation-testing scratch dir names seen in production repos — a name that is
    # ALL dots-and-word-chars (no leading './') must pass through completely unmolested.
    assert _clean_directory_token("./..hidden-double-dot/") == "..hidden-double-dot"
