"use client";

import { useMemo, useState } from "react";
import type { CountryKpi } from "@/lib/api";
import {
  COUNTRY_LOCKER_COLOR,
  COUNTRY_META,
  COUNTRY_PUDO_COLOR,
  isPreLaunch,
} from "@/lib/countries";
import { fmt1, fmtInt } from "@/lib/format";

export function CountryShare({ rows }: { rows: CountryKpi[] }) {
  // Split active vs pre-launch (SE/DK/FI all-zero rows).
  const active = useMemo(
    () => rows.filter((r) => !isPreLaunch(r.country) && r.n_total > 0),
    [rows],
  );
  const preLaunch = useMemo(
    () => rows.filter((r) => isPreLaunch(r.country)),
    [rows],
  );

  const totals = useMemo(() => {
    const lockers = active.reduce((s, r) => s + r.n_lockers, 0);
    const pudo = active.reduce((s, r) => s + r.n_pudo, 0);
    return { lockers, pudo };
  }, [active]);

  const lockersOrder = useMemo(
    () => [...active].sort((a, b) => b.n_lockers - a.n_lockers),
    [active],
  );
  const pudoOrder = useMemo(
    () => [...active].sort((a, b) => b.n_pudo - a.n_pudo),
    [active],
  );
  const totalOrder = useMemo(
    () => [...active].sort((a, b) => b.n_total - a.n_total),
    [active],
  );

  const [hovered, setHovered] = useState<string | null>(null);
  const hoveredKpi = hovered
    ? active.find((r) => r.country === hovered) ?? null
    : null;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-6 flex-wrap">
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 22,
            fontWeight: 300,
            letterSpacing: "-0.02em",
            lineHeight: 1.1,
          }}
        >
          Where the network sits
        </h2>
        <p className="max-w-prose" style={{ fontSize: 12.5, color: "var(--fg-muted)" }}>
          {active.length} active markets, two halves of the network. Each bar is the EU total — segments are countries.
        </p>
      </div>

      <article
        className="flex flex-col gap-4 px-6 py-5"
        style={{
          background: "var(--bg-surface-1)",
          border: "1px solid var(--border-subtle)",
        }}
        onMouseLeave={() => setHovered(null)}
      >
        <ShareRow
          category="Lockers"
          subtitle="parcel locker machines"
          total={totals.lockers}
          rows={lockersOrder}
          totalKpi="n_lockers"
          kind="lockers"
          hovered={hovered}
          onHover={setHovered}
        />
        <ShareRow
          category="PUDO"
          subtitle="partner pickup points"
          total={totals.pudo}
          rows={pudoOrder}
          totalKpi="n_pudo"
          kind="pudo"
          hovered={hovered}
          onHover={setHovered}
        />

        <ShareReadout
          hoveredKpi={hoveredKpi}
          totalLockers={totals.lockers}
          totalPudo={totals.pudo}
        />

        <ShareGrid
          rows={totalOrder}
          hovered={hovered}
          onHover={setHovered}
        />

        {preLaunch.length > 0 && (
          <div className="mt-1 flex items-center gap-4 flex-wrap">
            <span
              className="uppercase"
              style={{
                fontSize: 10.5,
                letterSpacing: "0.08em",
                color: "var(--fg-subtle)",
              }}
            >
              Pre-launch markets
            </span>
            <div className="flex gap-2 flex-wrap">
              {preLaunch.map((c) => {
                const meta = COUNTRY_META[c.country];
                return (
                  <div
                    key={c.country}
                    className="mono inline-flex items-center gap-2 px-3 py-2"
                    style={{
                      border: "1px dashed var(--border-strong)",
                      fontSize: 11.5,
                      color: "var(--fg-muted)",
                      background:
                        "repeating-linear-gradient(45deg, rgba(158, 37, 32, 0.12) 0 2px, transparent 2px 6px), var(--bg-surface-1)",
                    }}
                  >
                    <span className="flag" style={{ fontSize: 14 }}>
                      {meta?.flag}
                    </span>
                    <span>{c.country}</span>
                    <span>{meta?.name ?? c.country}</span>
                    <span style={{ color: "var(--fg-subtle)", fontSize: 10 }}>
                      catalog only · zero operational
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </article>
    </section>
  );
}

function ShareRow({
  category,
  subtitle,
  total,
  rows,
  totalKpi,
  kind,
  hovered,
  onHover,
}: {
  category: string;
  subtitle: string;
  total: number;
  rows: CountryKpi[];
  totalKpi: "n_lockers" | "n_pudo";
  kind: "lockers" | "pudo";
  hovered: string | null;
  onHover: (code: string | null) => void;
}) {
  const colorMap = kind === "lockers" ? COUNTRY_LOCKER_COLOR : COUNTRY_PUDO_COLOR;
  return (
    <div className="share-row grid items-center gap-3 md:gap-6 grid-cols-1 md:[grid-template-columns:220px_1fr]">
      <div className="share-label-row flex flex-col gap-0.5">
        <span
          className="uppercase"
          style={{
            fontSize: 11,
            letterSpacing: "0.08em",
            color: "var(--fg-muted)",
          }}
        >
          {category}
        </span>
        <span
          className="tnum share-total-num"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 36,
            fontWeight: 300,
            color: "var(--fg-default)",
            lineHeight: 1,
            letterSpacing: "-0.03em",
            marginTop: 4,
            marginBottom: 4,
          }}
        >
          {fmtInt(total)}
        </span>
        <span style={{ fontSize: 11, color: "var(--fg-subtle)" }}>{subtitle}</span>
      </div>
      <div
        className="flex w-full relative"
        style={{
          height: 38,
          background: "var(--bg-inset)",
          border: "1px solid var(--border-subtle)",
          cursor: "crosshair",
        }}
      >
        {rows.map((r, i) => {
          const v = r[totalKpi];
          if (v <= 0) return null;
          const w = (v / total) * 100;
          if (w < 0.4) return null;
          const isHovered = hovered === r.country;
          const dimmed = hovered != null && !isHovered;
          return (
            <div
              key={r.country}
              onMouseEnter={() => onHover(r.country)}
              data-country={r.country}
              className="relative flex items-center justify-center overflow-hidden cursor-pointer"
              style={{
                width: `${w.toFixed(3)}%`,
                height: "100%",
                background: colorMap[r.country] ?? "var(--border-default)",
                borderRight: i < rows.length - 1 ? "1px solid rgba(10,10,11,0.7)" : "none",
                opacity: dimmed ? 0.35 : 1,
                filter: isHovered ? "brightness(1.18)" : "none",
                transition: "opacity .15s ease, filter .15s ease",
                minWidth: 0,
                zIndex: isHovered ? 2 : 1,
              }}
            >
              {w >= 3.2 && (
                <span
                  className="mono"
                  style={{
                    fontSize: 10.5,
                    letterSpacing: "0.02em",
                    color:
                      kind === "lockers"
                        ? "rgba(10, 10, 11, 0.9)"
                        : "var(--fg-default)",
                    fontWeight: 600,
                    pointerEvents: "none",
                    whiteSpace: "nowrap",
                  }}
                >
                  {r.country}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ShareReadout({
  hoveredKpi,
  totalLockers,
  totalPudo,
}: {
  hoveredKpi: CountryKpi | null;
  totalLockers: number;
  totalPudo: number;
}) {
  const styleBase: React.CSSProperties = {
    borderTop: "1px solid var(--border-subtle)",
    paddingTop: 14,
    minHeight: 56,
    fontSize: 12.5,
    color: "var(--fg-muted)",
    display: "flex",
    alignItems: "center",
  };
  if (!hoveredKpi) {
    return (
      <div style={styleBase}>
        <span style={{ color: "var(--fg-subtle)", fontSize: 12 }}>
          Hover a country segment to inspect — or scan the table below.
        </span>
      </div>
    );
  }
  const meta = COUNTRY_META[hoveredKpi.country];
  const lockerShare =
    totalLockers > 0 ? (hoveredKpi.n_lockers / totalLockers) * 100 : 0;
  const pudoShare = totalPudo > 0 ? (hoveredKpi.n_pudo / totalPudo) * 100 : 0;
  return (
    <div style={styleBase}>
      <div className="share-readout-grid grid items-center gap-x-5 gap-y-3.5 w-full" style={{ gridTemplateColumns: "28px auto 1fr auto auto auto auto" }}>
        <span className="flag" style={{ fontSize: 22 }}>
          {meta?.flag}
        </span>
        <div>
          <span style={{ fontSize: 14, color: "var(--fg-default)", fontWeight: 500 }}>
            {meta?.name ?? hoveredKpi.country}
          </span>{" "}
          <span className="mono" style={{ fontSize: 10.5, color: "var(--fg-subtle)" }}>
            {hoveredKpi.country}
          </span>
        </div>
        <div />
        <StatBlock label="Total" value={fmtInt(hoveredKpi.n_total)} />
        <StatBlock
          label="Lockers"
          value={
            <>
              <span style={{ color: "var(--accent)" }}>
                {fmtInt(hoveredKpi.n_lockers)}
              </span>
              <span style={{ color: "var(--fg-subtle)", fontSize: 11 }}>
                {" · "}
                {fmt1(lockerShare)}% of EU
              </span>
            </>
          }
        />
        <StatBlock
          label="PUDO"
          value={
            <>
              {fmtInt(hoveredKpi.n_pudo)}
              <span style={{ color: "var(--fg-subtle)", fontSize: 11 }}>
                {" · "}
                {fmt1(pudoShare)}% of EU
              </span>
            </>
          }
        />
        <StatBlock label="24/7 access" value={`${fmt1(hoveredKpi.pct_247 ?? null)}%`} />
      </div>
    </div>
  );
}

function StatBlock({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span
        className="uppercase"
        style={{ fontSize: 10, letterSpacing: "0.06em", color: "var(--fg-subtle)" }}
      >
        {label}
      </span>
      <span
        className="tnum"
        style={{ fontSize: 14, color: "var(--fg-default)", letterSpacing: "-0.01em" }}
      >
        {value}
      </span>
    </div>
  );
}

function ShareGrid({
  rows,
  hovered,
  onHover,
}: {
  rows: CountryKpi[];
  hovered: string | null;
  onHover: (code: string | null) => void;
}) {
  // Responsive grid driven by a single --cells var. Mobile shows 4 cols,
  // tablet 6, desktop the full per-country layout — matches the design's
  // compact-card density.
  const cols = Math.max(rows.length, 1);
  return (
    <div
      className="share-cells grid pt-3.5"
      style={
        {
          ["--cells" as string]: cols,
          borderTop: "1px solid var(--border-subtle)",
        } as React.CSSProperties
      }
    >
      {rows.map((c, i) => {
        const lockerPct = c.n_total > 0 ? (c.n_lockers / c.n_total) * 100 : 0;
        const meta = COUNTRY_META[c.country];
        const isHovered = hovered === c.country;
        return (
          <div
            key={c.country}
            onMouseEnter={() => onHover(c.country)}
            className="cursor-pointer transition-colors flex flex-col gap-1.5 px-2 py-2.5 relative"
            style={{
              borderRight:
                i < rows.length - 1 ? "1px solid var(--border-subtle)" : "none",
              background: isHovered ? "var(--bg-surface-3)" : "transparent",
            }}
          >
            {c.country === "DE" && (
              <span
                className="absolute"
                style={{ left: 0, right: 0, top: 0, height: 2, background: "var(--accent)" }}
              />
            )}
            <div className="flex items-center gap-1.5">
              <span className="flag" style={{ fontSize: 18, lineHeight: 1 }}>
                {meta?.flag}
              </span>
              <span
                className="mono"
                style={{
                  fontSize: 10,
                  color: "var(--fg-muted)",
                  letterSpacing: "0.04em",
                }}
              >
                {c.country}
              </span>
            </div>
            <div
              className="tnum"
              style={{
                fontSize: 14,
                color: "var(--fg-default)",
                letterSpacing: "-0.015em",
              }}
            >
              {fmtInt(c.n_total)}
            </div>
            <div
              className="flex w-full"
              style={{ height: 3, background: "var(--bg-inset)", marginTop: 2 }}
            >
              <span
                style={{
                  height: "100%",
                  width: `${lockerPct.toFixed(2)}%`,
                  background: "var(--accent)",
                }}
              />
              <span style={{ height: "100%", flex: 1, background: "var(--border-strong)" }} />
            </div>
            <div
              className="tnum"
              style={{ fontSize: 10.5, color: "var(--fg-subtle)" }}
            >
              {fmt1(c.pct_247 ?? null)}% · 24/7
            </div>
          </div>
        );
      })}
    </div>
  );
}
