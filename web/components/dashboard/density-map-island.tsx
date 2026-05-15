/**
 * Client-island wrapper for the density map.
 *
 * MapLibre touches `window` at module-eval time, which blows up under SSR.
 * Wrapping the real DensityMap component in next/dynamic with ssr:false
 * keeps the rest of page.tsx server-rendered while deferring the map to the
 * browser. The skeleton mirrors the panel's outer shape so the layout
 * doesn't reflow when the map hydrates.
 */
"use client";

import dynamic from "next/dynamic";

const DensityMap = dynamic(
  () => import("./density-map").then((m) => m.DensityMap),
  {
    ssr: false,
    loading: () => <MapSkeleton />,
  },
);

export function DensityMapIsland() {
  return <DensityMap />;
}

function MapSkeleton() {
  return (
    <div
      className="panel relative animate-pulse"
      style={{ minHeight: 540, background: "var(--bg-inset)" }}
    >
      <div className="panel-head">
        <div>
          <div className="panel-title">Locker density by NUTS-2 region</div>
          <div className="panel-sub">Loading vector tiles…</div>
        </div>
      </div>
    </div>
  );
}
