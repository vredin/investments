---
name: clean-code
description: Pragmatic coding standards - concise, direct, no over-engineering, no unnecessary comments
allowed-tools: Read, Write, Edit
version: 2.1
---

# Clean Code — Pragmatic AI Coding Standards

> Full conventions are in `docs/CONVENTIONS.md` — this skill is a quick-reference reminder.

## Core Rules

1. **Write code directly** — don't explain what you're about to do, just do it
2. **Let code self-document** — if a name needs a comment, rename it
3. **Functions: small, single-purpose** — max 30 lines, max 3 args, one level of abstraction
4. **Guard clauses over nesting** — early returns, flat code
5. **No dead code** — delete it, don't comment it out
6. **No magic numbers** — use named constants
7. **DRY** — if writing same logic twice, extract

## Before Editing Any File

1. Check what imports this file — dependents might break
2. Check what tests cover this — tests might need updating
3. Edit file + all dependents in the SAME task

## After Editing

1. Verify no `console.log`, `print()`, `debugger`, `TODO`, `FIXME` left
2. Verify lint/type-check passes
3. Verify no broken imports

## When NOT to Apply

- Prototyping / spike — speed over cleanliness
- Generated code — don't clean what will be regenerated
- Third-party code — don't reformat vendored code
