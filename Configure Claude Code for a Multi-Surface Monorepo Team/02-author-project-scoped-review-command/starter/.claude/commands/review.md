---
description: Run the team's PR review checklist against a pull request or local diff
argument-hint: <pr-number | "HEAD~1..HEAD" | path/to/file>
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git status:*)
  - Bash(gh pr view:*)
  - Bash(gh pr checks:*)
---

# /review — team PR review

You are reviewing the diff identified by `$ARGUMENTS` against this repository's conventions. Apply the path-scoped rules in `.claude/rules/` (they auto-load based on the files touched) and the shared standards in `.claude/standards/`.

## Phase 1 — Interview pattern

Before reporting a finding, ask clarifying questions whenever the author's intent is ambiguous and the answer could change the review verdict. Do not assume intent when the diff has an unclear purpose.

Interview the author before reporting findings when:

- The change modifies dependencies in `package.json` or `pyproject.toml` without explaining why the dependency is needed.
- The change modifies a public API response shape, request contract, or database column and the intended compatibility behavior is unclear.
- The change is a refactor with no corresponding test changes and it is unclear whether existing tests already cover the behavior.
- The change touches multiple surfaces such as API handlers, React components, and database modules, but the intended end-to-end behavior is unclear.

Ask the minimum clarifying questions needed to establish intent. After the author's answer, apply the review criteria and report only findings supported by the clarified intent.

## Phase 2 — Review criteria

### Must report

- **Bugs:** Report logic errors, missing `await`, race conditions, and off-by-one errors.
- **Security:** Report raw SQL with user input, missing authentication, missing authorization, secrets in code, and unsafe `dangerouslySetInnerHTML`.
- **Convention violations:** Report violations of applicable path-scoped rules and shared standards.
- **Breaking changes:** Report changes that break existing API contracts, consumers, or interfaces.
- **Migration safety:** Report migrations that can lose data, fail for existing records, or cannot safely run against current data.

### Always skip

- **Minor formatting:** Do not block on formatting that automated tools such as Prettier handle.
- **Naming bikeshed:** Do not report naming preferences when the existing name is clear and follows repository conventions.
- **Personal style:** Do not report preferences that are not encoded in rules or standards.
- **Tracked TODOs:** Do not report TODOs that already have tracked tickets.
- **Non-actionable preferences:** Do not report feedback without a concrete correctness, security, compatibility, migration, or convention issue.

## Phase 3 — Bundling: interacting vs. independent findings

Bundle interacting findings into one detailed message when they overlap or require the same fix. Report independent findings sequentially as separate items when they occur in separate functions or files and do not share a fix.

Heuristic: if fixing A changes the code B references, they are interacting; otherwise, treat them as independent.

For interacting findings, explain all related problems in one finding and give one coordinated fix recommendation. For independent findings, give each finding its own severity, location, description, and fix.

## Phase 4 — Output format

For each finding, produce:

[severity] path/to/file.ts:line

finding: <one-sentence description>

fix: <one-sentence recommendation>

Severity is `bug` | `security` | `convention` | `breaking`. End with a one-line verdict: `approve`, `comment`, or `request-changes`.

## Examples

### Example 1 — Independent findings

Input

diff --git a/src/api/orders/handler.ts b/src/api/orders/handler.ts
@@
export async function getOrder(req, res) {
  const order = await orderService.get(req.params.id);

  if (!order) {
-    throw new ApiError(404, "Order not found");
+    return res.status(404).json({ status: 404 });
  }

-  return res.json(order);
+  const rows = await db.query(
+    "SELECT * FROM orders WHERE id = $1",
+    [req.params.id]
+  );
+  return res.json(rows[0]);
}

Output

[convention] src/api/orders/handler.ts:5

finding: The handler returns an ad-hoc `{ status: 404 }` response instead of using the project's `ApiError` convention.

fix: Throw `ApiError(404, "Order not found")` so API errors use the shared error-handling contract.

[convention] src/api/orders/handler.ts:8

finding: The handler bypasses the repository layer by calling the database directly with `db.query(...)`.

fix: Move the database access behind the appropriate repository module under `src/db/`.

comment

These findings are independent because they require separate fixes.

### Example 2 — Interacting findings

Input

diff --git a/src/api/refunds/refundOrder.ts b/src/api/refunds/refundOrder.ts
@@
export async function refundOrder(req, res) {
-  await paymentService.refund(req.body.paymentId);
-  await db.transaction(async (tx) => {
-    await refundRepository.create(tx, req.body.orderId);
-  });
+  paymentService.refund(req.body.paymentId);
+  refundRepository.create(req.body.orderId);
+  await orderRepository.markRefunded(req.body.orderId);
  return res.json({ ok: true });
}

Output

[bug] src/api/refunds/refundOrder.ts:4

finding: The refund operation is not awaited, the refund record is created without the transaction wrapper, and the payment/refund database writes are no longer coordinated atomically.

fix: Await the payment operation and restore the transaction wrapper so the payment operation, refund creation, and order update execute in the intended coordinated order.

request-changes

These problems are interacting because they share one coordinated fix.

## Notes

- This command is project-scoped (`.claude/commands/review.md`) so everyone on the team gets the same review. If you want to layer personal preferences (e.g. a stricter accessibility check on your own PRs), put a `~/.claude/commands/review-strict.md` in your home directory — it will not affect teammates.

- If a finding requires running code or modifying files to verify, ask the author to run a specific check rather than attempting it from the review session. This command's `allowed-tools` are read-only by design.