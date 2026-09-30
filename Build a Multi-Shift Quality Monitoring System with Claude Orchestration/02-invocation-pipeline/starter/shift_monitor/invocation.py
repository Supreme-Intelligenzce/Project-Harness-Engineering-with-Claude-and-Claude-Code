"""Three invocation shapes.

thin     — prompt only.
rich     — hot state + new defects.
resumed  — prior partial findings + new defects since the last manifest step.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .state import HotState

InvocationShape = Literal["thin", "rich", "resumed"]


@dataclass(frozen=True)
class Invocation:
    shape: InvocationShape
    prompt: str


def thin(prompt: str) -> Invocation:
    return Invocation(shape="thin", prompt=prompt)


def rich(
    role: str, hot_state: HotState, new_defects: Sequence[Mapping[str, Any]]
) -> Invocation:
    lines = [
        f"You are the on-call {role} for Northridge Plant 3.",
        "",
        "## Current hot state",
        f"- recent_defect_hashes: {hot_state.recent_defect_hashes}",
        f"- current_shift_summary: {hot_state.current_shift_summary}",
        f"- active_alerts: {hot_state.active_alerts}",
        f"- threshold_statuses: {hot_state.threshold_statuses}",
        "",
        "## New defects since last shift",
    ]

    if new_defects:
        for defect in new_defects:
            lines.append(
                "- "
                f"id={defect['id']}; "
                f"ts={defect['ts']}; "
                f"shift={defect['shift']}; "
                f"component={defect['component']}; "
                f"severity={defect['severity']}; "
                f"description={defect['description']}"
            )
    else:
        lines.append("- (none)")

    lines.extend(
        [
            "",
            "Provide:",
            "1. Summary",
            "2. Findings",
            "3. Recommended actions",
            "4. An Updated hot state proposal as a JSON block containing "
            "current_shift_summary, active_alerts, and threshold_statuses.",
        ]
    )

    return Invocation(shape="rich", prompt="\n".join(lines))


def resumed(
    session_id: str,
    summary: str,
    latest_message: str,
    prior_steps: Sequence[Mapping[str, Any]],
    new_defects: Sequence[Mapping[str, Any]],
) -> Invocation:
    lines = [
        f"Resume session: {session_id}",
        "",
        "## Prior partial findings",
    ]

    if prior_steps:
        for step in prior_steps:
            name = step.get("name", "(unnamed)")
            payload = repr(step.get("payload", ""))
            lines.append(f"- {name}: {payload[:500]}")
    else:
        lines.append("- (none)")

    lines.extend(
        [
            "",
            "## Prior summary",
            summary,
            "",
            "## New defects since last partial step",
        ]
    )

    if new_defects:
        for defect in new_defects:
            lines.append(
                "- "
                f"id={defect['id']}; "
                f"ts={defect['ts']}; "
                f"component={defect['component']}; "
                f"severity={defect['severity']}; "
                f"description={defect['description']}"
            )
    else:
        lines.append("- (none)")

    lines.extend(
        [
            "",
            "## Latest instruction",
            latest_message,
        ]
    )

    return Invocation(shape="resumed", prompt="\n".join(lines))