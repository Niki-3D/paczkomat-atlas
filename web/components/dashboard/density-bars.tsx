import type { Nuts2TopList } from "@/lib/api";
import type { DensityBenchmark } from "./hero-kpis";
import { fmt1, fmt2 } from "@/lib/format";

export function DensityBars({
  rows,
  benchmark,
}: {
  rows: Nuts2TopList[];
  benchmark: DensityBenchmark;
}) {
  const max = rows.length > 0 ? Math.max(...rows.map((r) => r.lockers_per_10k)) : 1;
  // Benchmark + ratio computed live in page.tsx::computeBenchmark from
  // listNuts2(limit=500). NEVER hardcode "2.24" / "10.06" / "4.5×" —
  // those values shift whenever the daily ingest refreshes the MVs.
  const nonPl = benchmark?.topNonPl;
  const topPl = benchmark?.topPl;
  const ratio = benchmark?.ratio ?? null;
  const annotLeftPct = nonPl ? (nonPl.density / max) * 100 : 0;

  return (
    <article
      className="flex flex-col panel panel-bars"
      style={{ minHeight: 540 }}
    >
      <header className="panel-head">
        <div>
          <div className="panel-title">Top 15 NUTS-2 regions by density</div>
          <div className="panel-sub">
            All 15 are Polish voivodeships. The dashed line shows the densest non-PL region for comparison.
          </div>
        </div>
        <div
          className="uppercase mono"
          style={{
            fontSize: 10.5,
            color: "var(--fg-subtle)",
            letterSpacing: "0.06em",
          }}
        >
          lockers / 10k
        </div>
      </header>

      <div className="flex-1 relative flex flex-col gap-1.5 px-5 py-3">
        {rows.map((row, i) => {
          const widthPct = (row.lockers_per_10k / max) * 100;
          return (
            <div
              key={row.code}
              className="grid items-center gap-2.5 relative"
              style={{
                gridTemplateColumns: "22px 142px 1fr 52px",
                height: 22,
              }}
            >
              <div
                className="mono text-right"
                style={{ fontSize: 11, color: "var(--fg-subtle)" }}
              >
                {i + 1}
              </div>
              <div
                className="truncate"
                style={{ color: "var(--fg-default)", fontSize: 12 }}
                title={row.name_latn}
              >
                {row.name_latn}
              </div>
              <div
                className="overflow-hidden relative"
                style={{
                  height: 14,
                  background: "var(--bg-inset)",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${widthPct.toFixed(2)}%`,
                    background: "var(--accent)",
                    position: "relative",
                  }}
                />
              </div>
              <div
                className="text-right tnum"
                style={{
                  fontSize: 12.5,
                  fontWeight: 500,
                  color: "var(--fg-default)",
                }}
              >
                {fmt2(row.lockers_per_10k)}
              </div>
            </div>
          );
        })}

        {/* Densest-non-PL benchmark line. Label + position pulled from the
            live benchmark prop (see computeBenchmark in page.tsx). Thicker
            accent-tinted dash + a single chip above the line communicates
            "this is the comparison reference, not a data row". */}
        {nonPl && (
          <div
            className="pointer-events-none absolute"
            style={{
              top: 16,
              bottom: 16,
              left: `calc(20px + 22px + 10px + 142px + 10px + ((100% - 20px - 22px - 10px - 142px - 10px - 52px - 10px - 20px) * ${(annotLeftPct / 100).toFixed(4)}))`,
              width: 1,
              borderLeft: "1.5px dashed var(--accent-lo)",
              zIndex: 2,
            }}
          >
            <div
              className="mono absolute whitespace-nowrap"
              style={{
                top: -12,
                left: 4,
                fontSize: 10,
                color: "var(--accent)",
                fontWeight: 500,
                padding: "2px 6px",
                background: "var(--bg-surface-1)",
                border: "1px solid var(--accent-lo)",
              }}
            >
              {nonPl.name} {fmt2(nonPl.density)} — top non-PL region
            </div>
          </div>
        )}
      </div>

      <footer
        className="flex flex-wrap items-center gap-1.5 px-5 py-2.5"
        style={{
          borderTop: "1px solid var(--border-subtle)",
          fontSize: 11,
          color: "var(--fg-muted)",
        }}
      >
        Top 15 by density are{" "}
        <span style={{ color: "var(--fg-default)", fontWeight: 500 }}>
          all Polish voivodeships
        </span>
        {nonPl && topPl && ratio != null && (
          <>
            . The dashed line marks {nonPl.name} ({nonPl.country}) at{" "}
            <span className="mono">{fmt2(nonPl.density)}</span> — the densest non-PL region.{" "}
            {topPl.name} at <span className="mono">{fmt2(topPl.density)}</span> is{" "}
            <span style={{ color: "var(--accent)", fontWeight: 500 }}>
              {fmt1(ratio)}× denser
            </span>
            .
          </>
        )}
      </footer>
    </article>
  );
}
