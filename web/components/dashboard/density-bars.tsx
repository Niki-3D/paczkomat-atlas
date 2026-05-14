import type { Nuts2TopList } from "@/lib/api";
import { fmt2 } from "@/lib/format";

const BUDAPEST_BENCHMARK = 2.24;

export function DensityBars({ rows }: { rows: Nuts2TopList[] }) {
  const max = rows.length > 0 ? Math.max(...rows.map((r) => r.lockers_per_10k)) : 1;
  const annotLeftPct = (BUDAPEST_BENCHMARK / max) * 100;

  return (
    <article
      className="flex flex-col panel panel-bars"
      style={{ minHeight: 540 }}
    >
      <header className="panel-head">
        <div>
          <div className="panel-title">Top 15 NUTS-2 regions by density</div>
          <div className="panel-sub">
            All 15 are Polish voivodeships. 16th place: <span className="mono">PL Mazowieckie</span> at 7.43.
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

        {/* Budapest benchmark line — annotation made unmistakably a comparison
            reference, not a stray data point. Thicker accent-tinted dash, label
            spells out the comparison in a single sentence above the line. */}
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
            Budapest 2.24 — top non-PL region
          </div>
        </div>
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
        . The dashed line marks Budapest (HU) at 2.24 — the densest non-PL region.
        Wielkopolskie at 10.06 is{" "}
        <span style={{ color: "var(--accent)", fontWeight: 500 }}>4.5× denser</span>.
      </footer>
    </article>
  );
}
