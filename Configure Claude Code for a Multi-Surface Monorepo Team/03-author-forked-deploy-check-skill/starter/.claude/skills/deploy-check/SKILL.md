---
name: deploy-check
description: Run the team's read-only pre-deployment validation checks against the current working tree and branch
context: fork
argument-hint: "[target-branch]: optional branch to compare against; defaults to main"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(gh pr view:*)
  - Bash(gh pr checks:*)
---

# /deploy-check

Runs the team's pre-deployment validation checklist against the current working tree and the branch you're about to ship. Read-only by design — this skill never modifies files, never pushes, never deploys. It returns a single structured summary so the calling session can decide whether to proceed.

## Why this is a skill (not a CLAUDE.md addition)

Skill: on-demand, forked, and task-specific; use it right before a deploy when verbose intermediate work such as file enumeration, diff parsing, and check execution has no value once the summary is known.
CLAUDE.md: always-loaded and universal; use it for conventions every session needs, such as tests being co-located or throwing `ApiError` for validation failures.
Rule of thumb: on-demand / forked / task-specific → skill; always-loaded / universal → CLAUDE.md.

## Why `context: fork`

The goal of `context: fork` is to keep verbose intermediate output OUT OF THE MAIN SESSION / conversation. The deploy check can walk the working tree, inspect diffs, enumerate files, and run several validation checks; none of that verbose output has value in the calling session once the structured pass-or-fail summary is known. Only that structured summary should return to the main conversation. `context: fork` is a Claude Code product feature operating at the skill-invocation layer, conceptually analogous to the Architect's Playbook *Branching Reality* pattern, where `fork_session` provides session-level isolation.

## Checks

Run all three. Each check produces a pass-or-fail verdict; if any fails, the overall summary is **fail**.

### Check 1 — Uncommitted changes

**Detect:** Run `git status --porcelain` against the current working tree.

**Pass:** The command returns no output, meaning there are no uncommitted or untracked changes.

**Fail:** The command returns one or more entries. Surface the affected paths in the check detail so the author can commit, stash, or otherwise resolve the changes before deployment.

### Check 2 — Migrations up-to-date with code

**Detect:** Compare the diff against the target branch with `git diff` and inspect changed repository/model code for new schema dependencies or repository imports; verify that each required schema change is backed by a migration file in the same branch.

**Pass:** Every new repository or schema dependency introduced by the diff has a corresponding migration, and there are no missing migration files required for the code changes.

**Fail:** A code change requires a migration that is missing or not present in the branch. Surface the affected model/repository change and the missing migration in the check detail so the author can add or verify the migration before deployment.

### Check 3 — CI checks green

**Detect:** Run `gh pr view --json statusCheckRollup` for the open pull request and inspect the required check conclusions.

**Pass:** All required CI checks report `SUCCESS`, with no required check pending, skipped unexpectedly, or failing.

**Fail:** One or more required checks are not successful. Surface the check name and its reported status in the check detail so the author knows which CI result must be resolved before deployment.

## Output format

Return exactly this shape to the main session:



Do not include the raw `git status`, raw diff hunks, or full check logs in the returned summary — those stay in the fork. If the author wants to investigate a failed check, they can re-invoke the skill targeting that single check or run the underlying command themselves.

## Personalization

This skill is project-scoped at `.claude/skills/deploy-check/`, so the whole team gets the same pre-deployment checks from version control. A teammate who wants a stricter personal variant, such as one that also fails when the diff exceeds 500 lines without a long enough PR description, can create a parallel skill at `~/.claude/skills/deploy-check-strict/` with a different name. That personal variant is not committed to the repository and does not affect teammates.

## What this skill deliberately does not do

- It never pushes, deploys, or runs migrations. The `allowed-tools` allowlist is read-only by construction; even if a future maintainer adds `Write` here, the team's `/review` command should catch the change.

- It does not run the test suite. Tests have their own pre-merge gate in CI; duplicating that here would slow every deploy check without adding signal.

- It does not check for secrets in code. That's the job of the `gitleaks` pre-commit hook, which fails the commit, not the deploy.