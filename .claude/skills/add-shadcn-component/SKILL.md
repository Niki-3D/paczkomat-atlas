---
name: add-shadcn-component
description: Use when adding a shadcn/ui component to the web/ workspace. Installs via shadcn CLI, ensures theme tokens.
allowed-tools: Read, Edit, Write, Bash, Glob
---

1. `cd web && pnpm dlx shadcn@latest add <component>`
2. Verify file landed in `web/components/ui/<component>.tsx`.
3. Replace hard-coded colors with `var(--…)` from `.claude/rules/design-tokens.md`.
4. If the component renders a number, ensure `font-mono tabular-nums`.
5. If interactive, ensure focus ring uses `--accent` not Tailwind default.
