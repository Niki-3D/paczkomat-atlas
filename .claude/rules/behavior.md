# Claude Code Behavior

## Before starting work

- Read `CLAUDE.md` and the relevant rule files for the task.
- State assumptions before non-trivial work:
  `ASSUMPTIONS: 1. X, 2. Y → Proceeding unless corrected`
- For multi-step tasks (>3 steps), show the plan first:
  `PLAN: 1. X, 2. Y, 3. Z → Executing unless redirected`

## When confused

STOP. Name the confusion. Ask one clarifying question. Wait.

Never guess on:
- Data ingest filters (test data, null island, dedup logic)
- Geometry SRID choices
- Materialized view refresh strategy
- API response shapes (the InPost API silently ignores unknown params — assume nothing)
- Public API contracts (route signatures, response schemas)

Smart assumptions OK for:
- UI layout, copy, naming
- Logging format
- Test structure
- Internal helper organization

## Scope discipline

- Touch only what's asked.
- No unsolicited refactoring.
- No removing code without approval.
- No adding deps without justification — note why in commit body.
- No changing rules files without approval — they encode decisions, not preferences.
- No changing CI workflows without flagging.
- No editing migrations after they've shipped — create new ones.

## Long-running command protocol

You may run heavy commands (ingest, migrations, builds). You must babysit:

1. After launching: check output within 10s. If it errored, fix and retry — don't move on.
2. While running: check progress every 30–60s.
3. If stuck (no output >2min): investigate — process alive? DB locks? memory?
4. On error: kill, analyze, fix root cause, retry. Never "it failed" without fixing.
5. On completion: verify with a COUNT query or output summary. Don't assume success.

NEVER fire-and-forget. NEVER let a background task run unmonitored.

If expected runtime >10min: tell user the estimate, ask whether to run it or hand off to their terminal. Their call.

## Push back

When you disagree:
1. State the problem clearly.
2. Explain the downside.
3. Propose an alternative.
4. Accept if overridden.

Push back especially on:
- Adding heavy deps when simpler works
- Premature optimization
- Bypassing the design tokens
- Bypassing data quality filters at ingest
- Skipping migration for "just this once" schema change
- Inline SQL when an ORM query works

## After completing

Summarize: what changed, what NOT touched, concerns to verify.

If schema changed: confirm migration created + Alembic head matches.
If new dep added: confirm justified in commit body + size impact noted.
If new endpoint: confirm response schema matches Pydantic model + typed in `web/lib/types.ts`.

## Pre-change blast radius check

Before modifying these critical files, read full file + understand all callers:
- `api/src/paczkomat_atlas_api/config.py`
- `api/src/paczkomat_atlas_api/db.py`
- `api/src/paczkomat_atlas_api/ingest/inpost_client.py`
- `infra/compose/docker-compose.yml`
- Any Alembic migration
- `.github/workflows/*.yml`
- `web/app/globals.css`
- `.claude/rules/*.md`

State what could break before you change them.
