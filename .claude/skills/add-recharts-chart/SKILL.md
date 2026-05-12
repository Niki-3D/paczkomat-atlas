---
name: add-recharts-chart
description: Use when adding a chart to the dashboard. Follows paczkomat-atlas chart conventions.
allowed-tools: Read, Edit, Write, Glob
---

1. Use shadcn `<ChartContainer>` wrapper.
2. No vertical gridlines, dashed hover cursor, axis ticks Geist Mono 11px `--fg-subtle`, no axis lines, no tick marks.
3. Area/Bar fills: `<linearGradient>` from `--accent` 0.4 → 0.0 opacity.
4. Strokes 1.5px, `--accent`.
5. `isAnimationActive={true}` on mount, `{false}` on update.
6. Custom `<ChartTooltipContent>` only — never default Tooltip.
7. Spawn `chart-stylist` for final review.
