---
name: orchestrate
description: 'Run the task orchestrator — executes backlog tasks one by one using the full dev workflow. Usage: /orchestrate [T-NNN]'
---

> **Style:** Load `caveman-distillate` skill — terse responses, no filler, fragments OK.

Use the orchestrator agent to execute tasks from `docs/TASK.md`.

Arguments: $ARGUMENTS

If arguments specify a task ID (e.g. `T-009`) — start with that task.
Otherwise — start with the first In Progress task, or the first Backlog task if nothing is in progress.
