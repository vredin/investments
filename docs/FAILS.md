# FAILS — Known Failure Patterns

> After every non-trivial error: add an entry here.
> Before starting any task: scan this file for similar patterns.
> This is an append-only catalogue — never delete entries.

Auto-published to Outline `Knowledge Base / Fails` (cross-project) via `/fix` STEP 7.
For full Outline contract: see `docs/OUTLINE-CONTRACT.md`.

---

## How to Read This File

Each entry is `F-NNN: <slug>` with sections:
- **Symptom** — user-visible behavior or error
- **Root cause** — technical why
- **Fix pattern** — what to apply when the same class recurs
- **Detection** — grep pattern or file pattern to spot in other code

Add entries via `/fix` STEP 7 (auto-numbered) or manually following the format.

---

## F-001: docker-compose env_file corrupts bcrypt hashes

**Symptom**: Bcrypt password hashes (`$2b$12$...`) get truncated/corrupted when
container starts. Login fails for accounts whose hashes contain `$VAR`-like patterns.

**Root cause**: `docker-compose.yml` `env_file:` directive performs shell-style
variable interpolation on values. Strings like `$2b`, `$12`, `$argon2id` look like
variable references → expanded to empty string → hash mangled.

**Fix pattern**: Mount `.env` as a **volume** instead of using `env_file`. Let
the application read the raw file directly (e.g. via `pydantic-settings`
`env_file=".env"` config). No shell interpolation in volume mount.

```yaml
# WRONG:
services:
  app:
    env_file: .env

# RIGHT:
services:
  app:
    volumes:
      - ./.env:/app/.env:ro
```

**Detection**:
```bash
grep -rn "env_file:" docker-compose*.yml
```
If any service has `env_file:` AND any env var holds `$`-containing secrets
(bcrypt, argon2, certain JWT secrets) → migrate to volume mount.

**Origin**: commit `e756b1a` (2026-05-04). Recorded retroactively per /self-audit
finding 4 on 2026-05-08.

---

## F-002: openpyxl on untrusted xlsx — zip-bomb + memory exhaustion

**Symptom**: Server OOM or hang when processing user-uploaded `.xlsx`. Attacker
uploads a 4KB file that decompresses to several GB.

**Root cause**: `openpyxl.load_workbook()` accepts any zip stream. xlsx files are
zip-archives; nested compressed payloads can expand thousands of times.

**Fix pattern** (defense in depth):
1. **Size cap before parse**: `file.read(MAX_BYTES+1)` to detect oversize *before*
   buffering full payload. If `len > MAX_BYTES` → reject with 413.
2. **Magic bytes check**: confirm `PK\x03\x04` zip signature before passing to openpyxl.
3. **`keep_links=False`** in `load_workbook(...)` — prevents external link resolution
   that can trigger SSRF.
4. **Bytes validator** as a separate function (`_validate_xlsx_bytes`) called before
   any sheet parsing.

```python
_MAX_XLSX_BYTES = 5 * 1024 * 1024  # 5 MB

def _validate_xlsx_bytes(data: bytes) -> None:
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError("not a valid xlsx (zip magic missing)")
    if len(data) > _MAX_XLSX_BYTES:
        raise ValueError("xlsx exceeds size cap")
```

**Detection**:
```bash
grep -rn "load_workbook\|openpyxl" --include="*.py" .
```
For every match: verify size cap + magic bytes check + `keep_links=False` exist
before the parse call.

**Origin**: commit `8eac09a` (2026-05-05), Rex RED findings SEC-001/002/003.
Recorded retroactively per /self-audit finding 4 on 2026-05-08.

---

<!-- Backfill complete for known cases. Remaining 2 retroactive entries
     mentioned by audit not auto-recoverable from git log alone. Add via /fix
     STEP 7 when next bug reproduces something previously seen. -->
