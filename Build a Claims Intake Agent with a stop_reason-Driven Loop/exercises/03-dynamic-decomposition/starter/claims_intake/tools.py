from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .session import ClaimSession


CLAIM_TYPES = ["property_damage", "theft", "liability", "auto"]
SEVERITIES = ["low", "medium", "high"]


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "lookup_policy",
        "description": (
            "Look up the policy associated with the claim. "
            "Use this early to understand policy coverage and relevant details."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_id": {
                    "type": "string",
                    "description": "The policy identifier to look up.",
                }
            },
            "required": ["policy_id"],
        },
    },
    {
        "name": "record_claim_fact",
        "description": (
            "Record one concrete fact about the claim. "
            "Use this as facts are learned from the claimant."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "The name of the claim fact.",
                },
                "value": {
                    "type": "string",
                    "description": "The value of the claim fact.",
                },
            },
            "required": ["field", "value"],
        },
    },
    {
        "name": "classify_claim",
        "description": (
            "Classify the claim into exactly one claim type and provide "
            "a confidence score and rationale."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_type": {
                    "type": "string",
                    "enum": CLAIM_TYPES,
                    "description": "The most appropriate claim type.",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence in the classification, from 0 to 1.",
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this claim type was selected.",
                },
            },
            "required": ["claim_type", "confidence", "rationale"],
        },
    },
    {
        "name": "assess_severity",
        "description": (
            "Assess the severity of the claim as low, medium, or high "
            "and provide the rationale."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": SEVERITIES,
                    "description": "The severity of the claim.",
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this severity was selected.",
                },
            },
            "required": ["severity", "rationale"],
        },
    },
    {
        "name": "request_clarification",
        "description": (
            "Ask the claimant one focused clarification question when "
            "the available facts leave multiple plausible claim types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "One focused clarification question.",
                },
                "ambiguity_between": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": CLAIM_TYPES,
                    },
                    "minItems": 2,
                    "description": (
                        "The claim types that are genuinely ambiguous "
                        "based on the current facts."
                    ),
                },
            },
            "required": ["question", "ambiguity_between"],
        },
    },
    {
        "name": "route_to_adjuster",
        "description": (
            "Route a sufficiently classified claim to the appropriate "
            "adjuster queue. This is a terminal action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "queue": {
                    "type": "string",
                    "enum": CLAIM_TYPES,
                    "description": "The adjuster queue to receive the claim.",
                },
                "claim_summary": {
                    "type": "string",
                    "description": "A concise summary of the claim.",
                },
            },
            "required": ["queue", "claim_summary"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Escalate a claim to a human reviewer when it cannot be "
            "classified confidently enough for automatic routing. "
            "This is a terminal action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why human review is required.",
                },
                "structured_summary": {
                    "type": "object",
                    "properties": {
                        "policy_id": {
                            "type": "string",
                            "description": "The policy identifier.",
                        },
                        "root_cause": {
                            "type": "string",
                            "description": "The known or suspected root cause.",
                        },
                        "candidate_claim_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": CLAIM_TYPES,
                            },
                            "description": (
                                "The plausible claim types still under consideration."
                            ),
                        },
                        "case_facts": {
                            "type": "object",
                            "description": "Facts collected about the claim.",
                        },
                        "recommended_action": {
                            "type": "string",
                            "description": "Recommended action for the human reviewer.",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Confidence in the current assessment.",
                        },
                    },
                    "required": [
                        "policy_id",
                        "root_cause",
                        "candidate_claim_types",
                        "case_facts",
                        "recommended_action",
                        "confidence",
                    ],
                },
            },
            "required": ["reason", "structured_summary"],
        },
    },
]


def _err(
    message: str,
    *,
    error_category: str = "permanent",
    is_retryable: bool = False,
) -> str:
    return json.dumps(
        {
            "is_error": True,
            "error_category": error_category,
            "is_retryable": is_retryable,
            "message": message,
        }
    )


def _ok(payload: Any) -> str:
    return json.dumps(payload)


def _t_lookup_policy(session: ClaimSession, args: dict[str, Any]) -> str:
    policy_id = args.get("policy_id")

    if not isinstance(policy_id, str) or not policy_id.strip():
        return _err("policy_id must be a non-empty string")

    policy = session.policies.get(policy_id)

    if policy is None:
        return _err(
            f"Policy not found: {policy_id}",
            error_category="permanent",
            is_retryable=False,
        )

    return _ok(policy)


def _t_record_claim_fact(session: ClaimSession, args: dict[str, Any]) -> str:
    field = args.get("field")
    value = args.get("value")

    if not isinstance(field, str) or not field.strip():
        return _err("field must be a non-empty string")

    if not isinstance(value, str):
        return _err("value must be a string")

    session.case_facts[field] = value

    return _ok(
        {
            "recorded": True,
            "field": field,
            "value": value,
        }
    )


def _t_classify_claim(session: ClaimSession, args: dict[str, Any]) -> str:
    claim_type = args.get("claim_type")
    confidence = args.get("confidence")
    rationale = args.get("rationale")

    if claim_type not in CLAIM_TYPES:
        return _err(
            f"claim_type must be one of: {', '.join(CLAIM_TYPES)}"
        )

    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return _err("confidence must be a number between 0 and 1")

    if not 0 <= confidence <= 1:
        return _err("confidence must be between 0 and 1")

    if not isinstance(rationale, str) or not rationale.strip():
        return _err("rationale must be a non-empty string")

    if session.classification is not None:
        return _err("classification has already been recorded")

    session.classification = {
        "claim_type": claim_type,
        "confidence": float(confidence),
        "rationale": rationale,
    }

    return _ok(
        {
            "classified": True,
            "claim_type": claim_type,
            "confidence": float(confidence),
        }
    )


def _t_assess_severity(session: ClaimSession, args: dict[str, Any]) -> str:
    severity = args.get("severity")
    rationale = args.get("rationale")

    if severity not in SEVERITIES:
        return _err(
            f"severity must be one of: {', '.join(SEVERITIES)}"
        )

    if not isinstance(rationale, str) or not rationale.strip():
        return _err("rationale must be a non-empty string")

    if session.severity is not None:
        return _err("severity has already been recorded")

    session.severity = {
        "severity": severity,
        "rationale": rationale,
    }

    return _ok(
        {
            "assessed": True,
            "severity": severity,
        }
    )


def _t_request_clarification(
    session: ClaimSession,
    args: dict[str, Any],
) -> str:
    question = args.get("question")
    ambiguity_between = args.get("ambiguity_between")

    if not isinstance(question, str) or not question.strip():
        return _err("question must be a non-empty string")

    if not isinstance(ambiguity_between, list):
        return _err("ambiguity_between must be a list")

    if len(ambiguity_between) < 2:
        return _err("ambiguity_between must contain at least two claim types")

    invalid_types = [
        claim_type
        for claim_type in ambiguity_between
        if claim_type not in CLAIM_TYPES
    ]

    if invalid_types:
        return _err(
            "ambiguity_between contains invalid claim types: "
            + ", ".join(str(value) for value in invalid_types)
        )

    session.clarifications_asked.append(
        {
            "question": question,
            "ambiguity_between": list(ambiguity_between),
        }
    )

    question_lower = question.lower()

    for key, reply in session.clarification_responses.items():
        if str(key).lower() in question_lower:
            return _ok(
                {
                    "reply": str(reply),
                }
            )

    return _ok(
        {
            "reply": "NO_RESPONSE",
        }
    )


def _t_route_to_adjuster(
    session: ClaimSession,
    args: dict[str, Any],
) -> str:
    if session.terminal_called:
        return _err("A terminal action has already been recorded")

    queue = args.get("queue")
    claim_summary = args.get("claim_summary")

    if queue not in CLAIM_TYPES:
        return _err(
            f"queue must be one of: {', '.join(CLAIM_TYPES)}"
        )

    if not isinstance(claim_summary, str) or not claim_summary.strip():
        return _err("claim_summary must be a non-empty string")

    if session.classification is None:
        return _err("classification must be set before routing")

    if session.severity is None:
        return _err("severity must be set before routing")

    classified_type = session.classification["claim_type"]

    if queue != classified_type:
        return _err(
            "queue must match the classified claim type"
        )

    record = {
        "claim_id": session.claim_id,
        "policy_id": session.policy_id,
        "claim_type": classified_type,
        "severity": session.severity["severity"],
        "confidence": session.classification["confidence"],
        "rationale": session.classification["rationale"],
        "claim_summary": claim_summary,
        "case_facts": dict(session.case_facts),
    }

    session.routing = record

    queue_path = session.run_dir / "queues" / f"{queue}.jsonl"
    _append_jsonl(queue_path, record)

    return _ok(
        {
            "routed": True,
            "queue": queue,
        }
    )


def _t_escalate_to_human(
    session: ClaimSession,
    args: dict[str, Any],
) -> str:
    if session.terminal_called:
        return _err("A terminal action has already been recorded")

    reason = args.get("reason")
    structured_summary = args.get("structured_summary")

    if not isinstance(reason, str) or not reason.strip():
        return _err("reason must be a non-empty string")

    if not isinstance(structured_summary, dict):
        return _err("structured_summary must be an object")

    required_fields = [
        "policy_id",
        "root_cause",
        "candidate_claim_types",
        "case_facts",
        "recommended_action",
        "confidence",
    ]

    missing = [
        field
        for field in required_fields
        if field not in structured_summary
    ]

    if missing:
        return _err(
            "structured_summary is missing required fields: "
            + ", ".join(missing)
        )

    policy_id = structured_summary["policy_id"]
    root_cause = structured_summary["root_cause"]
    candidate_claim_types = structured_summary["candidate_claim_types"]
    case_facts = structured_summary["case_facts"]
    recommended_action = structured_summary["recommended_action"]
    confidence = structured_summary["confidence"]

    if not isinstance(policy_id, str) or not policy_id.strip():
        return _err("structured_summary.policy_id must be a non-empty string")

    if not isinstance(root_cause, str) or not root_cause.strip():
        return _err("structured_summary.root_cause must be a non-empty string")

    if not isinstance(candidate_claim_types, list):
        return _err(
            "structured_summary.candidate_claim_types must be a list"
        )

    invalid_types = [
        claim_type
        for claim_type in candidate_claim_types
        if claim_type not in CLAIM_TYPES
    ]

    if invalid_types:
        return _err(
            "structured_summary.candidate_claim_types contains invalid "
            "claim types: "
            + ", ".join(str(value) for value in invalid_types)
        )

    if not isinstance(case_facts, dict):
        return _err("structured_summary.case_facts must be an object")

    if (
        not isinstance(recommended_action, str)
        or not recommended_action.strip()
    ):
        return _err(
            "structured_summary.recommended_action must be a non-empty string"
        )

    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return _err(
            "structured_summary.confidence must be a number between 0 and 1"
        )

    if not 0 <= confidence <= 1:
        return _err(
            "structured_summary.confidence must be between 0 and 1"
        )

    record = {
        "claim_id": session.claim_id,
        "policy_id": session.policy_id,
        "reason": reason,
        "root_cause": root_cause,
        "candidate_claim_types": list(candidate_claim_types),
        "case_facts": dict(case_facts),
        "recommended_action": recommended_action,
        "confidence": float(confidence),
        "case_facts_at_escalation": dict(session.case_facts),
    }

    session.escalation = record

    escalation_path = session.run_dir / "escalations.jsonl"
    _append_jsonl(escalation_path, record)

    return _ok(
        {
            "escalated": True,
        }
    )


_DISPATCH = {
    "lookup_policy": _t_lookup_policy,
    "record_claim_fact": _t_record_claim_fact,
    "classify_claim": _t_classify_claim,
    "assess_severity": _t_assess_severity,
    "request_clarification": _t_request_clarification,
    "route_to_adjuster": _t_route_to_adjuster,
    "escalate_to_human": _t_escalate_to_human,
}


def make_executor(session: ClaimSession) -> Executor:
    def execute(name: str, args: dict[str, Any]) -> str:
        handler = _DISPATCH.get(name)

        if handler is None:
            return _err(
                f"Unknown tool: {name}",
                error_category="permanent",
                is_retryable=False,
            )

        try:
            return handler(session, args)
        except Exception as exc:
            return _err(
                f"Tool execution failed: {exc}",
                error_category="transient",
                is_retryable=True,
            )

    return execute


Executor = Any


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")