---
name: anti-best-practice
description: "Use this skill when you encounter a failure, mistake, or unexpected error caused by your own actions, or when you learn a critical lesson that prevents future errors. It guides you in documenting the failure in the shared cross-project knowledge vault at {{VAULT_PATH}}/ (via the vault-write skill), building a repository of 'what not to do' and 'how to fix it' that all projects share."
---

# Anti-Best-Practice: The Art of Failing Forward

## Overview

This skill turns failures into cross-project assets. When you fumble, break something, or realize a "best practice" wasn't actually the best for this specific context, you MUST log it — but **not** to a local file. All fails, patterns, and gotchas are now stored in the shared vault at `{{VAULT_PATH}}/`, so every project you work on benefits from every lesson learned in every other project.

## When to Use

- **After a failed tool call sequence** that wasted time or resources.
- **When a 'fix' broke something else** (regression).
- **When you misunderstood the codebase** or environment.
- **When you violate a project rule** (e.g., language consistency, commit atomicity).
- **When you encounter a 'gotcha'** — a non-obvious truth about an API/service/config (classic example: "Meta test phone numbers silently drop real broadcasts").
- **When you hit a wrong assumption** about how a library, service, or internal module works.

## Workflow — delegate to vault-write

1.  **Analyze the failure** (before writing anything):
    *   **What happened?** (Symptom)
    *   **Why did it happen?** (Root cause — not the symptom, the cause)
    *   **How did you fix it?** (Fix)
    *   **How to catch it next time?** (Detection signals)
    *   **Is this reusable across projects?** If NO — don't log (it's project-specific, handle inline). If YES — proceed.

2.  **Classify the note type**:
    *   `fail` → reproducible bug with root cause + fix (something broke in runtime/tests)
    *   `gotcha` → wrong assumption about API/service/config, no code to fix — just document and avoid
    *   `pattern` → the FIX itself is a reusable solution worth naming (rare; most fails stay fails)

3.  **Invoke the `vault-write` skill** — it handles the full write protocol:
    *   Reads vault `CLAUDE.md` + `meta/taxonomy.md`
    *   Dedup check (grep before create)
    *   ID assignment, file creation, log.md append, hot.md update
    *   Git commit in the vault repo

See `.claude/skills/vault-write/SKILL.md` for the full procedure. Do not write to the vault directly without going through that skill — you will miss the dedup/contradiction/authorship protections.

## Guiding Principles

- **Be Honest**: Don't sugarcoat the mistake. If you hallucinated a library, say so.
- **Be Technical**: "I messed up" is not a reason. "I assumed `date-fns` was installed because `package.json` had similar dependencies" is a reason.
- **Focus on Detection**: The most important section of any vault note is "how to detect next time" — it should be actionable instructions a future Claude can grep for.
- **Cross-project lens**: Before writing, ask yourself "would a completely different project benefit from this?" If no, don't pollute the vault. Project-specific lessons live in that project's git history and code comments.
- **Classify correctly**: wrong-assumption notes are `gotchas`, not `fails`. The distinction matters for search: "I need to know API quirks before integration" pulls from gotchas, "I'm debugging a symptom" pulls from fails.

## What NOT to log in the vault

- Typos you fixed in your own code
- Linting errors
- One-off environment quirks on your machine
- Anything project-specific (framework version pinning for THIS project, DB schema for THIS product)
- Re-phrasings of official documentation that Context7 already delivers

The vault is for **cross-project, reusable, non-obvious** signals. If it's already obvious from docs or it only applies to one codebase — keep it out.
