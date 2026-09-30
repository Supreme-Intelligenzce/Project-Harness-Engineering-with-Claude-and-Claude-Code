# Reflection Brief — Harness Engineering Capstone

**Name:Pravin Kumar**
**Date:30/09/2026**

Replace each `→` with your answer. **Every answer cites at least one artifact from your own runs** — a run ID, file path, token count, claim outcome, or test count. Uncited answers do not pass. 3–6 sentences each unless noted. Paste short artifact snippets where they help.

**Environment**

- Model(s):Claude Haiku 4.5 and Claude Sonnet 4.6 for System 1; recorded/offline execution for System 4.
- OS / Python:Python 3.13.0.
- Approx. API spend:System 1 estimated $0.1276 for the Haiku run and $0.5847 for the Sonnet run, about $0.7123 total for those runs. System 4 used a recorded response for the verification run.

---

## Part 1 — Per-system

### System 1 — Agentic loop

1. **Loop control.** Quote the `stop_reason` sequence from one trace. Name the file and function that decides continue-vs-stop, and how.
   → In the Sonnet trace `runs/20260929_200110`, claim_02 has the sequence `tool_use → tool_use → tool_use → tool_use → tool_use → end_turn`; the routing tool is called on turn 5 and the model ends on turn 6. The continue-vs-stop decision is implemented in `claims_intake/loop.py`: the loop continues when `response.stop_reason == "tool_use"` and returns when `stop_reason == "end_turn"`. This makes the API's stop signal, rather than the assistant's prose, the loop-control mechanism.

2. **Anti-pattern.** Name one anti-pattern `test_antipatterns.py` checks for. What would break in your run if the loop used it?
   → One anti-pattern checked by `test_antipatterns.py` is using string-membership tests against assistant text as the loop's stopping signal. If the loop searched the model's prose for words such as a routing or completion phrase, a normal explanatory response could accidentally terminate the loop or fail to terminate it. The actual implementation instead relies on the API `stop_reason`, which is a structured signal. The anti-pattern tests therefore protect the central reliability property of the agentic loop.

3. **Tool design.** Pick two tools with overlapping inputs. How do the descriptions prevent misrouting? What did a structured tool error let the agent do that a generic string would not?
   → `classify_claim` and `request_clarification` both operate around incomplete or ambiguous claim information, but their descriptions establish different purposes: classification determines claim type and confidence, while clarification is used when required information is genuinely missing or ambiguous. The `classify_claim` description also says that confidence below 0.6 should prefer `escalate_to_human`. The terminal tools return structured errors through `_err`, including a permanent/non-retryable indicator and an explanatory message, rather than only an unstructured string. That lets the agent distinguish an invalid or permanent operation from something it can reasonably correct and retry.

4. **Your numbers.** Quote the turn count and cost for one claim. How does it differ from the README sample, and why?
   → In the Sonnet run `runs/20260929_200110/summary.md`, claim_02 took 6 turns and the complete run had an estimated cost of $0.5847; the artifact does not attribute that cost to individual claims. The Sonnet run produced 6 routed and 2 incomplete claims across 8 fixtures, which differs from the README's illustrative/sample behavior because the live model can choose different tool-call paths and stopping points. For example, claim_07 used `tool_use → end_turn` and therefore remained incomplete rather than reaching a terminal routing tool.

### System 2 — Context strategy

5. **The reduction.** From `budget.json`: baseline tokens, assembled tokens, reduction %. Which section dominates the assembled context, and why keep it verbatim?
   → System 2's `budget.json` records 38,708 baseline tokens and 16,949 assembled tokens, a 56.21% reduction. The `active` section dominates the assembled context at 15,789 tokens, compared with 204 for case facts, 465 for resolved refund, and 509 for resolved subscription. The active conversation is the unresolved/current part of the case, so preserving its detailed content avoids losing information that may still be needed for the next response.

6. **Summarize vs preserve.** State the rule for what gets summarized vs kept byte-exact, citing your per-section token numbers.
   → The rule is to summarize resolved information and preserve the active unresolved conversation in detail. In the run, case_facts was 204 tokens, resolved_refund was 465 tokens, and resolved_subscription was 509 tokens, while active remained 15,789 tokens. The resolved sections are compressed because their issues are already settled, while the active section is preserved because it may still contain information needed for the next response.

7. **Facts block.** Compare `eval.jsonl` to `eval_control.jsonl`. Which question regressed, and what does that prove?
   → The full-context eval.jsonl passed all 6 questions. In eval_control.jsonl, removing the case-facts block caused Q6 to fail as expected, while Q1 unexpectedly still passed. This shows that Q6 depended on the structured facts block, whereas the refund amount in Q1 was still recoverable from another part of the context. It also demonstrates why control evaluations are useful: they reveal both necessary information and redundant information.

### System 3 — Claude Code config

8. **Path-scoped rules.** Quote the glob frontmatter from one rule file. Why is it better than a directory-level CLAUDE.md for cross-cutting conventions?
   → The React rules use path-scoped frontmatter including `paths: - "src/components/**/*" - "src/pages/**/*"` in `.claude/rules/react.md`. This is better than putting the same convention in a directory-level `CLAUDE.md` when the convention crosses multiple directories, because one rule can target all matching paths without duplicating instructions in several directory files. The validator run for System 3 passed all 35 tests, confirming the expected path-scoped configuration.

9. **Forked skill.** Quote the `context: fork` and `allowed-tools` lines. What does running forked + read-only buy you? What breaks without it?
   → The deploy-check skill in `.claude/skills/deploy-check/SKILL.md` declares `context: fork` and uses a restricted `allowed-tools` list containing read-oriented tools such as Read, Grep, Glob, git status/diff/log/rev-parse/ls-files, and GitHub PR checks. Forking keeps the skill's verbose discovery output isolated from the main session, while the read-only allowlist prevents the skill from pushing, deploying, or modifying the repository. Without these controls, discovery output could consume the parent context and the validation workflow could have a larger side-effect surface. The System 3 validator completed with 35 passed tests.

10. **Scope.** From the validator output: project-level vs user-level scope. Give one example of each from this config.
    → The project-level scope is represented by `./CLAUDE.md`, which defines the shared repository conventions and hierarchy. The same configuration documents user-level scope under `~/.claude/CLAUDE.md`, `~/.claude/commands/`, and `~/.claude/skills/` for personal conventions and tools. The validator for this configuration returned `OK` and the complete test suite passed 35 tests, confirming the project configuration's expected hierarchy.

### System 4 — Orchestration

11. **Push work down.** Defects the SQL query returned vs warm-tier total. Name the indexed query. Why does the model never see the full history?
    → System 4's warm database contained 40 total defects, but the indexed query for the requested cutoff returned 0 defects after `2026-04-29T22:00:00Z`. `shift_monitor/warm.py` implements `SELECT * FROM defects WHERE ts > ? ORDER BY ts DESC LIMIT ?`, with indexes including `idx_defects_ts ON defects(ts)` and `idx_defects_shift_ts ON defects(shift, ts)`. `pipeline.py` calls this `defects_since` query before constructing the model input, so the model receives only the filtered slice rather than the full 40-record history. This is push-down work: the database performs filtering instead of spending model context on irrelevant history.

12. **Crash recovery.** The resume-vs-fresh decision and its staleness threshold (`recovery.py`). Why is a fresh start with an injected summary sometimes more reliable than resuming?
    → `shift_monitor/recovery.py` uses a 30-minute threshold: an incomplete state is resumed when its last step is no more than 30 minutes old, while an older state starts fresh. A fresh run can be more reliable when the previous intermediate state is stale or inconsistent because it avoids continuing from potentially invalid partial state while still allowing the previously captured summary to be injected as useful context. The implementation explicitly distinguishes resume from fresh-start behavior using `STALE_RESUME_THRESHOLD_MINUTES = 30`.

13. **Small state.** Byte size of your `hot_state.json`. Why does the budget matter for a system run once per shift, indefinitely?
    → My final System 4 `data/hot_state.json` was only 643 bytes. A system that runs once per shift indefinitely needs a bounded hot-state representation so state does not grow without limit and gradually increase context, storage, and processing costs. The small state also makes the system easier to recover and reason about between shifts. The System 4 verification completed with all 33 tests passing.

---

## Part 2 — Synthesis

*Graded on connecting two or more systems. Cite a named file/artifact from each.*

14. **Three layers.** Point to a file/artifact for each layer and justify.
    → Model:System 1's live trace in `runs/20260929_200110` shows Claude Sonnet making tool-use decisions and eventually producing `end_turn`.
    → Harness:System 1's `claims_intake/loop.py` enforces the stop_reason-driven execution loop, while System 3's validator enforces the Claude Code configuration structure.
    → Orchestration:System 4's `shift_monitor/pipeline.py`, warm database, hot state, and scratchpad coordinate work across a shift and across executions. The distinction is that the model makes semantic decisions, the harness constrains one interaction, and orchestration manages the larger workflow and state.

15. **Deterministic vs prompt.** Cite one behavior guaranteed in code (terminal tool, read-only allowlist, atomic write, byte budget) and one guided by prompt. When is each right?
    → A deterministic behavior is the System 1 terminal-loop rule in `claims_intake/loop.py`: `tool_use` continues the loop while `end_turn` stops it. A prompt-guided behavior is the tool guidance that classification confidence below 0.6 should prefer `escalate_to_human`. Deterministic enforcement is appropriate for safety-critical control flow and invariants that must not depend on model wording, while prompts are useful for semantic decisions where the model needs flexibility to interpret the case.

16. **Context, two faces.** Compare context management in System 2 (intra-session) and System 4 (cross-session) with cited numbers from both. Same principle, different mechanism — how?
    → System 2 manages context within one conversation: it reduced 38,708 baseline tokens to 16,949 assembled tokens, a 56.21% reduction, while preserving the 15,789-token active section. System 4 manages context across executions by querying the warm database for only defects after a cutoff and keeping a 643-byte hot state; in my verification there were 40 warm records but 0 after the requested cutoff. Both systems apply the same principle of retaining relevant state while discarding unnecessary history, but System 2 uses summarization/compression and System 4 uses persistent storage, indexed queries, and bounded state.

17. **Reliability you can't see in one run.** Name one behavior a test guarantees that a single successful run would not reveal. Why does it matter before shipping?
    → System 1's `test_antipatterns.py` guarantees that the loop does not use assistant-text string matching as its primary stopping mechanism. A single successful live run would not prove that this unsafe implementation pattern was absent because the correct outcome could happen accidentally. The test therefore protects an architectural invariant across future changes, which matters because reliability should survive refactoring rather than depend on one successful execution.

18. **Blast radius.** Pick one system. What's the blast radius if it misbehaves, and what's the kill switch? Ground it in that system's tools, enforcement points, and state.
    → For System 3, the deploy-check skill's blast radius is deliberately limited because it runs in a fork and has a read-only `allowed-tools` list. It can inspect repository state and CI/PR information, but the configuration explicitly prevents pushes, deployments, and migrations, so a misbehaving validation skill cannot directly perform those high-impact actions. The practical kill switch is simply not invoking the skill, while the fork and tool allowlist provide enforcement inside the workflow. This is a smaller blast radius than giving the same agent unrestricted shell or deployment access.

---

## Part 3 — Honest assessment

19. **What broke.** One thing that failed first try in your environment, and how you fixed it. (If nothing, what you checked to be sure.)
    → The first environment failure occurred in System 1 when the live Haiku run hit an `httpx`/Anthropic SDK compatibility error: `Client.__init__() got an unexpected keyword argument 'proxies'`. I fixed the environment by installing `httpx==0.27.2` in the System 1 virtual environment rather than changing the reference implementation. After that dependency fix, the System 1 test suite completed with 29 passed and the live Haiku and Sonnet runs completed.

20. **What you'd change.** One architectural decision you'd make differently, grounded in what you observed.
    → Based on the Sonnet run, I would add a deterministic postcondition around terminal completion rather than relying entirely on the model to call a terminal routing tool before `end_turn`. In `runs/20260929_200110`, 6 of 8 claims reached routing while claim_01 and claim_07 ended incomplete after `tool_use → end_turn`. The existing stop_reason-driven harness correctly respected the model's `end_turn`, but a separate policy could explicitly handle the case where `end_turn` occurs without a terminal outcome. This would preserve the stop_reason-driven design while making the business-level completion invariant more explicit.
