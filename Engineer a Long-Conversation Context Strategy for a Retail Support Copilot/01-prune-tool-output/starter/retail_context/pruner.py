"""Deterministic tool-output pruning for the verbose `lookup_order` response.

The "Tool Context Pruning" pattern: application-side filtering
of a verbose tool result so only the fields needed for the immediate decision survive
into context. For return/refund reasoning, exactly five fields matter — order identity,
when it was placed, what it cost, whether it shipped, and the return-window deadline.

Why each kept field is the only one that matters for return/refund reasoning:
  - order_id: Identifies the specific order the return or refund decision applies to.
  - order_date: Establishes when the order was placed and therefore when the return window started.
  - order_total_usd: Determines the order value that sets the monetary amount relevant to the refund decision.
  - fulfillment_status: Determines whether the request follows a fulfillment/cancellation or refund path.
  - return_eligible_until: Provides the deadline the agent compares against today's date to determine return eligibility.

Implementation: deterministic field selection (no LLM call). The pruner has no
`anthropic` import — enforced by an AST audit.
"""
from __future__ import annotations

KEPT_FIELDS: tuple[str, ...] = (
    "order_id",
    "order_date",
    "order_total_usd",
    "fulfillment_status",
    "return_eligible_until",
)


class PrunerMissingFieldError(KeyError):
    """Raised when the raw tool response is missing one of the required kept fields."""


def prune_lookup_order(raw: dict) -> dict:
    missing = [field for field in KEPT_FIELDS if field not in raw]

    if missing:
        raise PrunerMissingFieldError(
            f"Missing required field(s): {', '.join(missing)}"
        )

    return {field: raw[field] for field in KEPT_FIELDS}

