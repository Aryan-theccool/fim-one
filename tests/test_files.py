"""Tests for :mod:`fim_one.web.api.files` — the per-user index lock.

The lock is ``flock`` on POSIX and ``msvcrt.locking`` on Windows; both lock
per open file handle, so two holders in one process still exclude each other.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from fim_one.web.api import files


@pytest.fixture(autouse=True)
def _uploads(tmp_path: Path) -> Iterator[None]:
    with patch.object(files, "UPLOAD_ROOT", tmp_path):
        yield


class TestFileLock:
    @pytest.mark.asyncio
    async def test_second_holder_waits_for_release(self) -> None:
        order: list[str] = []
        first_holding = asyncio.Event()
        release_first = asyncio.Event()

        async def first() -> None:
            async with files._file_lock("u1"):
                order.append("first-acquired")
                first_holding.set()
                await release_first.wait()
                order.append("first-released")

        async def second() -> None:
            await first_holding.wait()
            async with files._file_lock("u1"):
                order.append("second-acquired")

        t1 = asyncio.create_task(first())
        t2 = asyncio.create_task(second())
        await first_holding.wait()
        await asyncio.sleep(0.3)
        assert "second-acquired" not in order

        release_first.set()
        await asyncio.wait_for(asyncio.gather(t1, t2), timeout=5)
        assert order == ["first-acquired", "first-released", "second-acquired"]

    @pytest.mark.asyncio
    async def test_lock_is_reacquirable_after_release(self) -> None:
        for _ in range(3):
            async with files._file_lock("u1"):
                pass

    @pytest.mark.asyncio
    async def test_users_do_not_block_each_other(self) -> None:
        async with files._file_lock("u1"):
            await asyncio.wait_for(self._hold("u2"), timeout=2)

    @staticmethod
    async def _hold(user_id: str) -> None:
        async with files._file_lock(user_id):
            pass

    @pytest.mark.asyncio
    async def test_index_round_trip_under_lock(self) -> None:
        async with files._file_lock("u1"):
            files._save_index("u1", {"f1": {"name": "a.txt"}})
            assert files._load_index("u1") == {"f1": {"name": "a.txt"}}
