"""Tests for ``_collect_dag_tools_used`` — the tool list on DAG completion cards."""

from __future__ import annotations

from typing import Any, Literal

from fim_one.core.planner import PlanStep
from fim_one.core.planner.types import StepOutput
from fim_one.web.api.chat import _collect_dag_tools_used


def _step(
    step_id: str,
    *,
    tool_hint: str | None = None,
    data: dict[str, Any] | None = None,
    has_result: bool = True,
    status: Literal["pending", "running", "completed", "failed", "skipped"] = "completed",
) -> PlanStep:
    result = StepOutput(summary="done", data=data) if has_result else None
    return PlanStep(
        id=step_id, task="t", tool_hint=tool_hint, result=result, status=status
    )


class TestCollectDagToolsUsed:
    def test_uses_recorded_tools_not_hints(self) -> None:
        steps = [
            _step(
                "s1",
                tool_hint="web_search",
                data={"step_type": "react", "tools_used": ["web_fetch", "python_exec"]},
            ),
        ]
        assert _collect_dag_tools_used(steps) == ["web_fetch", "python_exec"]

    def test_step_that_called_no_tools_contributes_nothing(self) -> None:
        steps = [
            _step("s1", tool_hint="web_search", data={"step_type": "react", "tools_used": []}),
        ]
        assert _collect_dag_tools_used(steps) == []

    def test_dedupes_across_steps_in_first_use_order(self) -> None:
        steps = [
            _step("s1", data={"step_type": "react", "tools_used": ["b", "a"]}),
            _step("s2", data={"step_type": "react", "tools_used": ["a", "c"]}),
        ]
        assert _collect_dag_tools_used(steps) == ["b", "a", "c"]

    def test_llm_direct_step_contributes_nothing(self) -> None:
        steps = [_step("s1", data={"step_type": "llm_direct"})]
        assert _collect_dag_tools_used(steps) == []

    def test_falls_back_to_hint_without_recorded_data(self) -> None:
        # e.g. a step restored from a checkpoint written before data existed
        steps = [_step("s1", tool_hint="sql_query", data=None)]
        assert _collect_dag_tools_used(steps) == ["sql_query"]

    def test_failed_step_without_record_does_not_report_hint(self) -> None:
        # A timed-out or crashed step never recorded tools; don't guess.
        steps = [_step("s1", tool_hint="sql_query", data=None, status="failed")]
        assert _collect_dag_tools_used(steps) == []

    def test_skipped_step_without_result_contributes_nothing(self) -> None:
        steps = [_step("s1", tool_hint="sql_query", has_result=False, status="skipped")]
        assert _collect_dag_tools_used(steps) == []
