# Scheduling /report — decision matrix

`/report` writes daily status to Outline `Knowledge Base / Daily Status` and to local `docs/reports/<date>.md`. Multiple ways to schedule it; pick one that matches your environment.

## Decision matrix

| Mechanism | Best when | Pros | Cons |
|---|---|---|---|
| **launchd** (macOS) | macOS user, Mac is on at scheduled time | Uses real local Claude setup (MCP, memory, project files). Free, no cloud cost. | Requires Mac awake at trigger time. macOS only. |
| **systemd timer** (Linux) | Linux dev box, always-on | Same advantages as launchd | Linux only. Service-level config required. |
| **Cloud `/schedule`** | GitHub repo connected AND Outline accessible from Anthropic cloud | Survives Mac off / sleep. Doesn't need local machine. | Currently blocked: Outline isn't in the Anthropic cloud connector catalog. Requires GitHub connector. |
| **`/loop` (in-session)** | Short-cadence within an active Claude Code session | Simple, no setup | Stops when session closes |
| **Manual** | Ad-hoc reports | Full control | Forgetful — defeats the point of automation |

## Recommended: launchd (macOS)

For most users on this template — daily-cadence automation with full local context.

Setup via `/setup` → mode **"Setup local /report scheduler (launchd)"**:
- Asks for desired report time (default: 23:00 local)
- Generates `bin/launchd-report.sh` from template (project-specific paths, claude binary, project dir)
- Generates `~/Library/LaunchAgents/com.<user>.<project>-report.plist`
- Prints `launchctl bootstrap` command for you to run
- Records configuration in `.claude/.setup.json` under `launchd.report`

Manual setup (if `/setup` mode unavailable):
1. Copy `bin/launchd-report.sh.template` → `bin/launchd-report.sh`. Replace placeholders:
   - `{{CLAUDE_BIN}}` → output of `which claude`
   - `{{PROJECT_PATH}}` → absolute path of your project
   - `{{LAUNCHD_LABEL}}` → e.g. `com.<user>.<project>-report`
   - `{{REPORT_HOUR}}` → desired hour (0-23)
2. `chmod +x bin/launchd-report.sh`
3. Copy `templates/launchd-report.plist.template` → `~/Library/LaunchAgents/<label>.plist`. Replace same placeholders + `{{HOME}}`.
4. `plutil -lint ~/Library/LaunchAgents/<label>.plist` (validate)
5. `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/<label>.plist` (load)
6. `launchctl list | grep <label>` (verify registered)
7. Test manually: `bin/launchd-report.sh` (runs the report immediately)

## When launchd isn't enough

Switch to **Cloud `/schedule`** as soon as both prerequisites are met:
1. GitHub connector connected via `/web-setup` (so cloud agent can clone repo)
2. Outline appears in Anthropic cloud connectors catalog (currently not — only Google Drive, etc.)

When that day comes:
```
/schedule "0 23 * * *" /report
```
And disable the launchd job: `launchctl bootout gui/$UID ~/Library/LaunchAgents/<label>.plist`

## Disabling launchd

```bash
launchctl bootout gui/$UID ~/Library/LaunchAgents/<label>.plist
rm ~/Library/LaunchAgents/<label>.plist
rm bin/launchd-report.sh   # optional — can keep for manual runs
```

Then update `.claude/.setup.json`: remove the `launchd.report` block.

## Logs

`~/Library/Logs/<label>.log` — all stdout + stderr from the wrapper and Claude.

```bash
tail -f ~/Library/Logs/com.semishan.investments-report.log
```

If launchd fires but nothing happens, check the log for:
- `claude binary not found` → wrong CLAUDE_BIN path in wrapper
- `project dir not found` → wrong PROJECT_PATH
- `MCP outline disconnected` → claude can't reach Outline; `/report` falls back to local-only
- `No activity for <project> on <date>` → report deliberately skipped (no commits, no task changes)

## Related

- `docs/OUTLINE-CONTRACT.md` — what `/report` writes to Outline
- `.claude/commands/report.md` — the command itself
