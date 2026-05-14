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
