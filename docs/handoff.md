# Session Handoff — 2026-05-08

## Completed This Session

- phase00-session01-skeleton: все 22 задачи [x], state.json обновлён, committed db0a34b
- phase01-session01-broker-sync: spec.md + tasks.md созданы (21 задача), state.json обновлён
- docs/DEPLOY.md: переписан на git-based deploy (git push + ssh vps3 git pull), committed 34f4387
- .spec_system/CONSIDERATIONS.md: vault lessons (F-038, F-048, F-041), исправлены записи, committed a3d5d1b
- memory/project_context.md: исправлен стек (→PostgreSQL+pgvector+OpenRouter), SSH alias, deploy command
- memory/vault_reference.md: создан, добавлен в MEMORY.md
- Git-deploy на VPS: deploy key на GitHub, сервер переключён с rsync на git pull, проверен push

## In Progress (not finished)

- /setup reconfigure MCP: пользователю показаны команды для reconnect outline MCP — ответа 'done' ещё не получено
- phase01-session01-broker-sync: реализация не начата (0/21 задач)

## Next Session Should

1. Проверить MCP: `claude mcp list | grep outline` — если не подключён, повторить /setup reconfigure
2. Запустить `/implement` для `phase01-session01-broker-sync` (21 задача)
3. T001 первым: `docker compose exec app python -c "import tradernet; help(tradernet.TraderNetAPI)"` — задокументировать реальные имена методов SDK

## Context That Would Be Lost

- Git deploy на сервере: `cd /opt/Investments && git pull origin main && docker compose up -d --build --no-deps app`
- SSH alias: `vps3` (docs/DEPLOY.md)
- GitHub remote: `git@github.com:vredin/investments.git`
- Deploy key на сервере: ed25519, comment `github-actions-cv-deploy`
- IBKR: Flex Query XML upload ONLY — CP Gateway не работает headless на VPS (решение зафиксировано)
- Freedom Finance: tradernet SDK, perpetual key в .env (FREEDOM_PUBLIC_KEY, FREEDOM_PRIVATE_KEY, FREEDOM_LOGIN, FREEDOM_PASSWORD)
- Vault fails применены: F-038 (Alembic ID ≤32 chars), F-048 (env-var data migrations при auto-run пропускаются), F-041 (verify deploy с curl)
- OpenRouter вместо Anthropic: openai SDK + base_url="https://openrouter.ai/api/v1" + OPENROUTER_API_KEY

## User's Last Unanswered Question

- Пользователь выбрал "Reconfigure MCP" в /setup. Показаны команды для reconnect outline. Ожидаем 'done'.

## Open Questions for User

- Outline MCP переподключил?
- /implement запускать сразу после /setup или в отдельной сессии?
