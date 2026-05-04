# Phase 00: Foundation

**Status**: Not Started
**Progress**: 0/1 sessions (0%)

## Overview

Set up the project skeleton: Python environment with uv, SQLite schema, Typer CLI, keyring wiring. After this phase, `assistant init` and `assistant --help` must work without errors.

## Progress Tracker

| Session | Name | Status | Validated |
|---------|------|--------|-----------|
| 00-01 | Project skeleton, schema, CLI, keyring | Not Started | No |

## Acceptance Criteria

- `uv init investments-assistant` + `pyproject.toml` with all pinned deps
- Folder structure: `src/`, `data/store/`, `data/imports/`, `reports/`, `logs/`, `tests/`
- SQLite schema created by `assistant init` (9 tables: config, instruments, prices, positions, transactions, external_balances, channel_signals, recommendations, progress_snapshots)
- `assistant init` populates `config.yaml` template
- `assistant --help` lists all subcommands
- ANTHROPIC_API_KEY stored/retrieved via macOS Keychain (keyring)
- All tests pass: `pytest tests/`

## Next Steps

Run `/plansession` to get Session 00-01 specification.
