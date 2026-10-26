"""Tests for scripts/eval_stamp.py, the pre-commit behavioral-eval guard.

Focus: watched paths must use ``/`` so they match git's output.  With
``\\`` on Windows no staged file ever matched and the guard always passed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "eval_stamp.py"
_spec = importlib.util.spec_from_file_location("eval_stamp_script", _SCRIPT)
assert _spec is not None and _spec.loader is not None
eval_stamp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eval_stamp)


class TestWatchedFiles:
    def test_paths_use_forward_slashes(self) -> None:
        files = eval_stamp.watched_files()
        assert files
        assert all("\\" not in f for f in files)

    def test_builtin_tools_are_watched_in_git_form(self) -> None:
        assert "src/fim_one/core/tool/builtin/file_ops.py" in eval_stamp.watched_files()

    def test_exact_entries_are_kept(self) -> None:
        files = eval_stamp.watched_files()
        for exact in eval_stamp.WATCHED_EXACT:
            assert exact in files
