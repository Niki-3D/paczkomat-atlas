# Code Quality

## Hard limits

| Metric | Limit |
|---|---|
| Function length | ≤30 lines (target ≤20) |
| File length | ≤300 lines (target ≤200) |
| Nesting depth | ≤3 levels |
| Function params | ≤3 positional before Pydantic/interface |
| Class methods | ≤10 per class |

Exceeding any of these is a smell, not a hard fail — but justify in commit body if you do.

## Python (api/)

REQUIRED:
- Type hints on every function (args + return). No exceptions.
- Pydantic v2 models for all data crossing module boundaries.
- pydantic-settings for config (already in `config.py`).
- `ruff` for lint + format (auto via PostToolUse hook).
- `async def` for anything doing I/O.
- Polars for data processing — never Pandas unless forced by a downstream lib.
- `structlog` for logging — never `print()`.
- f-strings for formatting.
- `match` statements over if/elif chains when ≥3 branches.
- `Decimal` for any value where precision matters.

ZERO TOLERANCE:
- Untyped functions
- `# type: ignore` without comment explaining why
- `print()` in non-script code (scripts/ may use it)
- Bare `except:`
- Mutable default arguments (`def f(x: list = [])`)
- `time.sleep()` in async code (use `asyncio.sleep`)
- Hardcoded URLs, addresses, magic numbers — use `config.py` or module-level constants
- `Any` without comment justifying it

## TypeScript (web/)

REQUIRED:
- `strict: true` in tsconfig (already set).
- Explicit return types on exported functions.
- Interface for component props (>1 prop).
- Named exports — `export function WalletCard()`. Default export ONLY for Next.js `page.tsx` / `layout.tsx`.
- Functional components only — no classes.

ZERO TOLERANCE:
- `any` anywhere
- `as` assertions without comment
- `@ts-ignore` / `@ts-expect-error` without comment
- Default exports on non-page files
- Raw `fetch()` outside `lib/api.ts`
- Inline `style={{}}` (use Tailwind utilities + CSS vars)
- `useEffect` for data fetching (use SWR or React Query)

## Naming

| Thing | Convention | Example |
|---|---|---|
| Python file | `snake_case.py` | `inpost_client.py` |
| Python class | `PascalCase` | `InPostClient` |
| Python function / var | `snake_case` | `fetch_lockers` |
| Python constant | `UPPER_SNAKE_CASE` | `MAX_PER_PAGE` |
| Pydantic schema | `{Thing}Schema` | `LockerSchema` |
| SQLAlchemy model | `{Thing}Model` | `LockerModel` |
| TS component file | `PascalCase.tsx` | `KpiCard.tsx` |
| TS hook file | `use-kebab-case.ts` | `use-locker-density.ts` |
| TS hook function | `useCamelCase` | `useLockerDensity` |
| TS type | `PascalCase` | `LockerScore` |
| CSS var | `--kebab-case` | `--bg-canvas` |

## General

- No commented-out code — delete it.
- Comments explain "why", never "what".
- No magic values — constants module or config.
- DRY: 2x duplication is a smell, 3x is a bug. Extract.
- Early returns over deep nesting.
- Composition over inheritance.
- One primary class per file.
- Imports: stdlib → third-party → local, blank line between groups.

## Error handling

- Domain exceptions in `api/src/paczkomat_atlas_api/exceptions.py` (create when first needed).
- Services raise domain exceptions → FastAPI handlers map to HTTP status codes.
- Worker loops: catch per-iteration, log context, continue.
- External API: retry with exponential backoff, raise after max retries.
- Log: what failed, which resource (locker name, country), state left behind.
- Rate-limit errors: back off and retry, never crash.
