"""Shift pipeline: SQL pre-filter, prompt build, single Claude call, atomic state update."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .client import ClaudeClient, Message
from .invocation import rich
from .scratchpad import Scratchpad, ScratchpadEntry
from .state import HOT_STATE_BYTE_BUDGET, MAX_RECENT_HASHES, HotState
from .warm import WarmStore

log = logging.getLogger(__name__)

JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass(frozen=True)
class ShiftResult:
    shift_id: str
    new_defect_count: int
    summary: str


def gather_new_defects(
    warm: WarmStore, since_ts: str, limit: int = 50
) -> list[dict[str, Any]]:
    return warm.defects_since(since_ts, limit=limit)


def build_rich_prompt(
    role: str, hot_state: HotState, new_defects: Sequence[Mapping[str, Any]]
) -> str:
    return rich(
        role=role,
        hot_state=hot_state,
        new_defects=new_defects,
    ).prompt

def _parse_hot_state_update(response_text: str) -> dict[str, Any] | None:
    match = JSON_FENCE_RE.search(response_text)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _short_summary_from_response(response_text: str, shift_id: str) -> str:
    for line in response_text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("```"):
            return stripped[:200]
    return f"Shift {shift_id}: no summary extracted."


def _new_hashes(new_defects: Sequence[Mapping[str, Any]], prior: Sequence[str]) -> list[str]:
    incoming = [d["id"] for d in new_defects]
    merged: list[str] = []
    for h in incoming + list(prior):
        if h not in merged:
            merged.append(h)
        if len(merged) >= MAX_RECENT_HASHES:
            break
    return merged


def _trim_to_budget(state: HotState) -> HotState:
    if len(state.to_json_bytes()) <= HOT_STATE_BYTE_BUDGET:
        return state
    alerts = list(state.active_alerts)
    while alerts and len(state.to_json_bytes()) > HOT_STATE_BYTE_BUDGET:
        alerts.pop()
        state = state.model_copy(update={"active_alerts": alerts})
    return state


def run_shift(
    shift_id: str,
    client: ClaudeClient,
    warm: WarmStore,
    hot_state_path: Path,
    scratchpad_path: Path,
    since_ts: str,
    role: str = "quality engineer",
) -> ShiftResult:
    # 1. Read the previous hot state.
    hot_state = HotState.from_path(hot_state_path)

    # 2. SQL-side retrieval of only new defects.
    new_defects = gather_new_defects(warm, since_ts)

    # 3. Build the rich invocation.
    prompt = build_rich_prompt(role, hot_state, new_defects)

    # 4. Exactly one Claude call.
    response = client.complete(
        [Message(role="user", content=prompt)]
    )
    response_text = response.content

    # 5. Parse the optional updated hot-state JSON.
    update = _parse_hot_state_update(response_text)

    if update is None:
        update = {}

    current_shift_summary = update.get(
        "current_shift_summary",
        hot_state.current_shift_summary,
    )

    active_alerts = update.get(
        "active_alerts",
        hot_state.active_alerts,
    )

    threshold_statuses = update.get(
        "threshold_statuses",
        hot_state.threshold_statuses,
    )

    # Keep the expected types if the model returns malformed values.
    if not isinstance(current_shift_summary, str):
        current_shift_summary = hot_state.current_shift_summary

    if not isinstance(active_alerts, list):
        active_alerts = hot_state.active_alerts

    if not isinstance(threshold_statuses, dict):
        threshold_statuses = hot_state.threshold_statuses

    # 6. Construct the updated hot state.
    updated_state = HotState(
        recent_defect_hashes=_new_hashes(
            new_defects,
            hot_state.recent_defect_hashes,
        ),
        current_shift_summary=current_shift_summary,
        active_alerts=active_alerts,
        threshold_statuses=threshold_statuses,
    )

    updated_state = _trim_to_budget(updated_state)

    # 7. Atomic state write.
    updated_state.write_atomic(hot_state_path)

    # 8. Append exactly one scratchpad entry.
    summary = _short_summary_from_response(response_text, shift_id)

    evidence = (
        f"Processed {len(new_defects)} new defects since {since_ts}. "
        f"Claude response: {response_text[:500]}"
    )

    conclusion = summary

    Scratchpad(scratchpad_path).append(
        ScratchpadEntry(
            hypothesis_id=f"shift-{shift_id}",
            evidence=evidence,
            conclusion=conclusion,
            ts=datetime.now(UTC),
        )
    )

    # 9. Return the shift result.
    return ShiftResult(
        shift_id=shift_id,
        new_defect_count=len(new_defects),
        summary=summary,
    )