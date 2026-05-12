# Design Tokens — Single source of truth

These tokens live in `web/app/globals.css` as CSS custom properties under `:root[data-theme="dark"]`. Reference via `var(--token)`. NEVER introduce a hex literal in components.

## Surfaces (warm-neutral, four-step elevation)
- `--bg-canvas: #0A0A0B`
- `--bg-surface-1: #111113`
- `--bg-surface-2: #18181B`
- `--bg-surface-3: #1F1F23`
- `--bg-inset: #08080A`

## Borders (hairline)
- `--border-subtle: #1F1F23`
- `--border-default: #27272A`
- `--border-strong: #3F3F46`

## Text (warm ivory — never pure white)
- `--fg-default: #EDEDEE`
- `--fg-muted: #A1A1A6`
- `--fg-subtle: #6B6B70`
- `--fg-disabled: #3F3F46`

## Accent (dialed-down InPost yellow)
- `--accent: #E0A82E`
- `--accent-hi: #F5C04E`
- `--accent-lo: #6B4F14`
- `--accent-fg: #0A0A0B`

## Semantic
- `--success: #34D399`
- `--warning: #FBBF24`
- `--danger: #F87171`
- `--info: #60A5FA`

## Choropleth (single-hue sequential amber)
- `--map-0: #1A1A1F`
- `--map-1: #2A2F1E`
- `--map-2: #524018`
- `--map-3: #8B6914`
- `--map-4: #C29612`
- `--map-5: #F5C04E`

## Typography
- `--font-sans: var(--font-geist-sans)`
- `--font-mono: var(--font-geist-mono)`

## Radii
- Cards/inputs: `rounded-md` (6px)
- Modals/popovers: `rounded-lg` (8px)
- Never `rounded-xl`+ on data UI.

## Forbidden
- `#FFFFFF` / `bg-white` / `text-white`
- `#000000` / `bg-black` / `text-black`
- Any hex not in this file
- Tailwind color classes that bypass tokens
- `box-shadow` on cards
