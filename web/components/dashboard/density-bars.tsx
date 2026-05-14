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

        {/* Budapest annotation line (track area starts at col-3 of the grid) */}
        <div
          className="pointer-events-none absolute"
          style={{
            top: 16,
            bottom: 16,
            left: `calc(20px + 22px + 10px + 142px + 10px + ((100% - 20px - 22px - 10px - 142px - 10px - 52px - 10px - 20px) * ${(annotLeftPct / 100).toFixed(4)}))`,
            width: 1,
            borderLeft: "1px dashed var(--fg-muted)",
            zIndex: 2,
          }}
        >
          <div
            className="mono absolute whitespace-nowrap"
            style={{
              top: -10,
              left: 4,
              fontSize: 10,
              color: "var(--fg-muted)",
              padding: "2px 6px",
              background: "var(--bg-surface-1)",
              border: "1px solid var(--border-default)",
            }}
          >
            Budapest · 2.24
          </div>
          <div
            className="mono absolute whitespace-nowrap"
            style={{
              bottom: -10,
              left: 4,
              fontSize: 10,
              color: "var(--fg-subtle)",
              padding: "2px 6px",
              background: "var(--bg-surface-1)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            densest non-PL region
          </div>
        </div>
      </div>

      <footer
        className="flex flex-wrap items-center gap-1.5 px-5 py-2.5"
        style={{
          borderTop: "1px solid var(--border-subtle)",
          fontSize: 11,
          color: "var(--fg-subtle)",
        }}
      >
        <span
          className="inline-block"
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "var(--accent)",
          }}
        />{" "}
        Polish voivodeship
        <span style={{ color: "var(--border-strong)", margin: "0 0.25em" }}>·</span>
        <span
          className="inline-block align-middle mr-0.5"
          style={{
            width: 18,
            borderTop: "1px dashed var(--fg-muted)",
          }}
        />{" "}
        non-PL benchmark
      </footer>
    </article>
  );
}
