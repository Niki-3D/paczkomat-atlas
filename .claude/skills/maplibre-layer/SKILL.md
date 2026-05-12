---
name: maplibre-layer
description: Use when adding a layer (choropleth, points, heatmap, clusters) to the MapLibre map.
allowed-tools: Read, Edit, Write, Glob
---

1. Add to `web/lib/map/layers.ts`. One exported function per layer.
2. Choropleth: `fill` + `line` (NEVER `fill-outline-color`).
3. Colors from `--map-0..--map-5` for sequential; teal↔amber for diverging.
4. Hover via `feature-state` — wire listeners in `useMapHover` hook (reuse, don't duplicate).
5. Zoom-based progressive disclosure: `interpolate ['zoom']` for opacity/size.
6. Sources lazy-loaded; layers added on `map.on('load')`.
7. Spawn `map-styler` for review.
