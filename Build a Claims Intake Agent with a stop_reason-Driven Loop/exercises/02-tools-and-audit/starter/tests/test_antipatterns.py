
"""Anti-pattern audit.

Verifies, by static AST analysis, that the agentic loop does NOT:
- use string-membership tests against text content to drive control flow
- use an integer-literal iteration cap as its primary stopping mechanism
- omit reference to `stop_reason` as the loop-breaking signal

And that the package broadly does not branch on `claim_type` equality
outside of the tool-schema definitions and the cost-estimate module.

Each test parses the relevant file with `ast` and walks the tree. There are
no runtime imports of claims_intake here — the audit is static, so it works
even if loop.py / tools.py do not run end-to-end.
"""

from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "claims_intake"
LOOP_PY = PKG / "loop.py"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# ---------------------------------------------------------------------------
# Anti-pattern 1 — no string-membership tests against assistant text in the loop
# ---------------------------------------------------------------------------
def test_no_string_membership_against_text_in_loop() -> None:
    """No `"some_token" in <something>` expressions in loop.py.

    Heuristic: any `ast.Compare` node using `ast.In` whose `left` operand is a
    string `ast.Constant` is flagged. The loop has no legitimate reason to test
    for the presence of a magic string inside the model's output — that would be
    natural-language-driven control flow.
    """
    tree = _parse(LOOP_PY)
    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if (
                    isinstance(op, ast.In)
                    and isinstance(node.left, ast.Constant)
                    and isinstance(node.left.value, str)
                ):
                    offenders.append(ast.unparse(node))

    assert offenders == [], (
        "loop.py contains string-membership tests against text: "
        f"{offenders}"
    )


# ---------------------------------------------------------------------------
# Anti-pattern 2 — no integer-literal iteration cap as the primary stop mechanism
# ---------------------------------------------------------------------------
def test_no_integer_literal_iteration_cap_in_loop() -> None:
    """No `for _ in range(<int literal>)` and no `while <var> < <int literal>` in loop.py.

    Token/wall-clock/config-sourced budgets are explicitly allowed because they
    read their cap from a `Budget` instance (an attribute access or a function
    arg), not from a literal. If you need a cap, pass it in.
    """
    tree = _parse(LOOP_PY)
    offenders: list[str] = []

    for node in ast.walk(tree):
        # Detect range(<integer literal>, ...)
        if isinstance(node, ast.For):
            iterator = node.iter

            if (
                isinstance(iterator, ast.Call)
                and isinstance(iterator.func, ast.Name)
                and iterator.func.id == "range"
                and iterator.args
                and any(
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, int)
                    and not isinstance(arg.value, bool)
                    for arg in iterator.args
                )
            ):
                offenders.append(ast.unparse(node))

        # Detect while <something> < <integer literal>
        elif isinstance(node, ast.While):
            test = node.test

            if isinstance(test, ast.Compare):
                for comparator in test.comparators:
                    if (
                        isinstance(comparator, ast.Constant)
                        and isinstance(comparator.value, int)
                        and not isinstance(comparator.value, bool)
                    ):
                        offenders.append(ast.unparse(node))
                        break

    assert offenders == [], (
        "loop.py contains an integer-literal iteration cap; "
        "use a Budget instead: "
        f"{offenders}"
    )


# ---------------------------------------------------------------------------
# Positive evidence — stop_reason is the value that breaks the while loop
# ---------------------------------------------------------------------------
def test_stop_reason_is_loop_control() -> None:
    """loop.py references `stop_reason` AND a `while` loop exits via return/raise on it."""
    tree = _parse(LOOP_PY)

    # 1. Confirm that stop_reason is referenced somewhere in the file.
    has_stop_reason_reference = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "stop_reason":
            has_stop_reason_reference = True
            break

        if isinstance(node, ast.Attribute) and node.attr == "stop_reason":
            has_stop_reason_reference = True
            break

    assert has_stop_reason_reference, (
        "loop.py does not reference stop_reason as loop-control state"
    )

    # 2. Confirm that a while-loop body references stop_reason and exits
    #    through return or raise.
    while_loops = list(
        node for node in ast.walk(tree) if isinstance(node, ast.While)
    )

    assert while_loops, "loop.py does not contain a while loop"

    matching_loop = False

    for while_node in while_loops:
        body_text = ast.unparse(while_node)

        has_stop_reason = "stop_reason" in body_text
        has_exit = "return" in body_text or "raise" in body_text

        if has_stop_reason and has_exit:
            matching_loop = True
            break

    assert matching_loop, (
        "while loop does not appear to use stop_reason with "
        "return/raise as its exit signal"
    )


# ---------------------------------------------------------------------------
# Decision-tree-in-Python — no `if claim_type == "..."` branches in the package
# ---------------------------------------------------------------------------
def test_no_claim_type_equality_branching_in_package() -> None:
    """Decision logic about claim type lives in the model, not in Python.

    tools.py is exempt (it defines the enum in input_schema).
    pricing.py is exempt (it may map claim_type to per-queue cost weights).
    """
    offenders: list[str] = []

    for path in PKG.rglob("*.py"):
        if path.name in {"tools.py", "pricing.py", "__init__.py"}:
            continue

        tree = _parse(path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue

            if not any(isinstance(op, ast.Eq) for op in node.ops):
                continue

            left = node.left

            left_is_claim_type = (
                isinstance(left, ast.Name)
                and left.id == "claim_type"
            ) or (
                isinstance(left, ast.Attribute)
                and left.attr == "claim_type"
            )

            if not left_is_claim_type:
                continue

            compares_to_string = any(
                isinstance(comparator, ast.Constant)
                and isinstance(comparator.value, str)
                for comparator in node.comparators
            )

            if compares_to_string:
                offenders.append(
                    f"{path.name}:{node.lineno}: {ast.unparse(node)}"
                )

    assert offenders == [], (
        "claim_type decision branching found in Python. "
        "Move the decision into the model via tool calls: "
        f"{offenders}"
    )

