# E-Commerce Platform — Shared Claude Code Conventions

This file is the **project-level** entry point for the e-commerce monorepo. Every teammate's Claude session loads it automatically.

## Scope: what belongs here vs. elsewhere

| Scope | Location | Purpose | Shared with teammates? |
|---|---|---|---|
| **Project-level** | `./CLAUDE.md`, `.claude/` | Team-shared conventions, standards, rules, commands, and skills for this repository. | **Yes**, through version control. |
| **User-level** | `~/.claude/` | Personal Claude Code preferences and conventions that should apply across the user's projects. | **No. User-level settings are NOT shared with teammates via version control.** |
| **Directory-level** | `CLAUDE.md` in a subdirectory | Conventions specific to a particular directory or subtree of the repository. | **Yes**, if committed to version control. |

For example, a preferred personal commit message style belongs at **user-level** because it is an individual preference rather than a team requirement. Team-wide commit conventions belong at project-level.

## Shared standards (modular via @-imports)

The actual conventions live in focused files so this entry point stays scannable:

@.claude/standards/frontend.md
@.claude/standards/api.md
@.claude/standards/database.md
@.claude/standards/testing.md

Path-scoped rules in [.claude/rules/](.claude/rules/) layer on top of these standards and activate only when Claude is editing matching files (React components, API handlers, test files).

## Repository layout

```text
src/components/   React components (functional + hooks)
src/pages/        Top-level routes
src/api/          Node.js API handlers
src/db/           PostgreSQL repository-pattern modules




## Troubleshooting

Run `/memory` to diagnose why a `CLAUDE.md` instruction is not taking effect.