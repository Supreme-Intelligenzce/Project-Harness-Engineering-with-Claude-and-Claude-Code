# Plan mode vs. direct execution — team decision guide

Choosing between Claude Code's **plan mode** (investigate and propose before changing anything) and **direct execution** (change code immediately) is the single biggest leverage point in how the team uses the harness day-to-day. The wrong mode at either extreme costs us: plan mode for trivial fixes is friction; direct execution for architectural changes burns context and produces rework.

> Knight-Webb, “SWE Is Becoming Plan and Review.” Source: Module 8 curriculum doc, Anchor Talks table.

This doc walks four concrete decisions against our codebase: one plan-mode example, one direct-execution example, one Explore-subagent example, and one combined-workflow example.

---

## 1. Plan-mode example

### Scenario

We want to extract the duplicated cart-state logic from `src/components/Cart/Cart.tsx`, `src/components/Checkout/Checkout.tsx`, and `src/components/MiniCart/MiniCart.tsx` into a shared `useCart(userId)` hook under a new hooks directory.

### Why plan mode

This is a large-scale, multi-file modification with multiple valid approaches and an architectural decision about where shared cart state should live and what the hook should own. The change affects three consumers, so the dependency and behavior boundaries should be understood before any files are edited.

Use plan mode to inspect the three existing implementations, compare their differences, identify the shared behavior, propose the hook interface, and identify the required updates to each consumer before making changes.

Planning first helps **prevent costly rework** by resolving the architectural choice and dependency impact before committing to an implementation. This maps directly to the Task 3.4 guidance for large-scale changes, multiple valid approaches, architectural decisions, and multi-file modifications.

---

## 2. Direct-execution example

### Scenario

Add `min: 0` validation to the quantity field handled by the order endpoint in `src/api/orders/handler.ts`.

### Why direct execution

This is a simple, well-scoped change targeting one function and one validation rule. The intended behavior is already clear: reject a negative quantity while preserving the existing handling for valid quantities.

The author already knows what the patch should look like before invoking Claude: add the minimum constraint, keep the surrounding handler behavior unchanged, and run the relevant tests.

The direct-execution bar is simple: **if you can describe the change in one sentence and predict the patch, skip planning.** This maps to Task 3.4's guidance for simple, well-scoped changes where investigation and architectural exploration would add unnecessary friction.

---

## 3. Explore-subagent example

### Scenario

Find every place the codebase calls `processRefund`, including calls that may not be obvious from a simple file-by-file inspection. Relevant locations include `src/api/orders/refund.ts`, `src/api/billing/issue.ts`, and `src/services/payment.ts`.

### Why use the Explore sub-agent

This is a discovery and inventory task rather than an implementation task. The goal is to isolate verbose discovery output from the main conversation and return a concise summary of the call sites, preserving the main conversation context for the actual decision or implementation that follows.

The Explore sub-agent can search the repository, inspect surrounding code, trace references, and record its working inventory without flooding the main session with every intermediate file enumeration and search result.

Use the **scratchpad pattern**: the discovery agent writes its working notes and call-site inventory to a scratchpad file such as tmp/refund-callsites.md. The scratchpad lets the inventory survive the main session's context window while the main session receives only the structured summary needed to continue.

This maps to Task 3.4's guidance for isolating verbose discovery output and returning summaries to preserve the main conversation context.

---

## 4. Combined workflow — plan mode for investigation, then direct execution

### Scenario

Rename `ordersRepo.findById` to `ordersRepo.getById` in `src/db/orders.ts` to align with the team's naming convention: `get*` for single-row reads and `find*` for multi-row reads.

The important part is that the rename looks mechanical only after the complete call-site list is known. Before editing, we need to determine where `findById` is called and whether any references are dynamic or constructed in a way that a simple grep could miss.

### Why use the combined workflow

This is the Task 3.4 pattern of **combining plan mode for investigation with direct execution for implementation**. Plan mode handles the uncertain discovery phase; once the scope is established, direct execution handles the mechanical rename.

1. **Plan mode investigates and proposes.** Inspect `src/db/orders.ts`, trace all `findById` references, investigate possible dynamic references, identify affected callers, and propose the complete rename plan.
2. **The author approves the plan.** Confirm that the discovered call-site list is complete and that the rename preserves the intended repository naming convention.
3. **Direct execution applies the rename and runs tests.** Once the scope is known, update the known references from `findById` to `getById` and run the relevant tests.

The combined workflow avoids using direct execution before the scope is known while also avoiding unnecessary planning during the mechanical implementation phase. It is the right shape when investigation is uncertain but the resulting change is predictable.

---

## Quick reference

| Situation | Mode |
|-----------|------|
| Single function, fix is obvious, you can predict the diff | Direct execution |
| Multi-file refactor, API shape is debatable | Plan mode |
| Discovery / inventory across the codebase, you'll throw away the intermediate steps | Explore subagent |
| Investigation-then-mechanical-change | Plan mode → direct execution |
| Architectural decision (which database, which queue) | Plan mode, possibly with a fork to compare options |

When in doubt: plan mode is recoverable (you can switch to execution), but direct execution on a complex change is not. Default to plan when uncertain.