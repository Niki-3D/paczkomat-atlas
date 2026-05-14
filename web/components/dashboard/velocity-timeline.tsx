"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { VelocityPoint } from "@/lib/api";
import { fmtInt } from "@/lib/format";

const SERIES = ["PL", "FR", "GB", "IT", "ES"] as const;
type SeriesCode = (typeof SERIES)[number];

const COLORS: Record<SeriesCode, { stroke: string; width: number }> = {
  PL: { stroke: "#F5C04E", width: 2.2 },
  FR: { stroke: "#A1A1A6", width: 1.6 },
  GB: { stroke: "#6B6B70", width: 1.6 },
  IT: { stroke: "#8B6914", width: 1.6 },
  ES: { stroke: "#3F3F46", width: 1.6 },
};

type Wide = { ts: number; date: string } & Partial<Record<SeriesCode, number>>;

function toWide(points: VelocityPoint[]): {
  data: Wide[];
  growth: Partial<Record<SeriesCode, number>>;
  lastByCountry: Partial<Record<SeriesCode, { ts: number; value: number }>>;
} {
  const byDate = new Map<string, Wide>();
  for (const p of points) {
    if (!(SERIES as readonly string[]).includes(p.country)) continue;
    const ts = new Date(p.date).getTime();
    const row = byDate.get(p.date) ?? { ts, date: p.date };
    row[p.country as SeriesCode] = p.n_lockers;
    byDate.set(p.date, row);
  }
  const data = [...byDate.values()].sort((a, b) => a.ts - b.ts);

  const growth: Partial<Record<SeriesCode, number>> = {};
  const lastByCountry: Partial<Record<SeriesCode, { ts: number; value: number }>> = {};
  for (const cc of SERIES) {
    const series = points
      .filter((p) => p.country === cc)
      .sort((a, b) => a.date.localeCompare(b.date));
    if (series.length >= 2) {
      const first = series[0].n_lockers;
      const last = series[series.length - 1].n_lockers;
      if (first > 0) growth[cc] = last / first;
      lastByCountry[cc] = {
        ts: new Date(series[series.length - 1].date).getTime(),
        value: last,
      };
    }
  }
  return { data, growth, lastByCountry };
}

function formatYearTick(ts: number): string {
  const d = new Date(ts);
  const m = d.getUTCMonth();
  if (m === 0) return String(d.getUTCFullYear());
  if (m === 6) return "Jul";
  return d.toISOString().slice(0, 7);
}

function formatTooltipDate(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function VelocityTimeline({ points }: { points: VelocityPoint[] }) {
  const { data, growth, lastByCountry } = useMemo(() => toWide(points), [points]);

  if (data.length === 0) {
    return (
      <article
        className="panel flex items-center justify-center"
        style={{ minHeight: 360 }}
      >
        <p style={{ color: "var(--fg-subtle)", fontSize: 12 }}>
          No velocity data available.
        </p>
      </article>
    );
  }

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
          Expansion velocity
        </h2>
        <p style={{ fontSize: 12.5, color: "var(--fg-muted)" }}>
          Locker counts from InPost public press releases · {formatTooltipDate(data[0].ts)} → {formatTooltipDate(data[data.length - 1].ts)}
        </p>
      </div>
      <article
        className="panel"
        style={{ padding: "20px 20px 8px" }}
      >
        <div style={{ width: "100%", minHeight: 360 }}>
          <ResponsiveContainer width="100%" height={360}>
            <LineChart
              data={data}
              margin={{ top: 16, right: 100, bottom: 24, left: 12 }}
            >
              <CartesianGrid
                vertical={false}
                stroke="var(--border-subtle)"
                strokeDasharray="0"
              />
              <XAxis
                type="number"
                dataKey="ts"
                domain={["dataMin", "dataMax"]}
                tickFormatter={formatYearTick}
                stroke="var(--border-default)"
                tick={{
                  fill: "var(--fg-subtle)",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                }}
                tickLine={false}
                axisLine={{ stroke: "var(--border-default)" }}
                scale="time"
              />
              <YAxis
                stroke="var(--border-default)"
                tick={{
                  fill: "var(--fg-subtle)",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                }}
                tickFormatter={(v: number) => (v === 0 ? "0" : `${(v / 1000).toFixed(0)}k`)}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ stroke: "var(--border-default)", strokeDasharray: "2 2" }}
                content={<TimelineTooltip />}
              />
              {SERIES.map((cc) => (
                <Line
                  key={cc}
                  type="monotone"
                  dataKey={cc}
                  stroke={COLORS[cc].stroke}
                  strokeWidth={COLORS[cc].width}
                  dot={{
                    r: cc === "PL" ? 2.8 : 2,
                    fill: COLORS[cc].stroke,
                    strokeWidth: 0,
                  }}
                  activeDot={{ r: 4, fill: COLORS[cc].stroke, strokeWidth: 0 }}
                  isAnimationActive={false}
                  connectNulls
                />
              ))}
              {SERIES.map((cc) => {
                const last = lastByCountry[cc];
                if (!last) return null;
                return (
                  <ReferenceDot
                    key={`${cc}-label`}
                    x={last.ts}
                    y={last.value}
                    r={0}
                    ifOverflow="extendDomain"
                    label={(props: { viewBox: { x: number; y: number } }) => {
                      const { x, y } = props.viewBox;
                      const g = growth[cc];
                      return (
                        <g>
                          <text
                            x={x + 8}
                            y={y + 4}
                            fill={COLORS[cc].stroke}
                            fontFamily="var(--font-sans)"
                            fontSize={11}
                            fontWeight={500}
                          >
                            {cc}
                          </text>
                          {g != null && (
                            <text
                              x={x + 30}
                              y={y + 4}
                              fill="var(--fg-muted)"
                              fontFamily="var(--font-mono)"
                              fontSize={10.5}
                            >
                              {g.toFixed(1)}×
                            </text>
                          )}
                        </g>
                      );
                    }}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <footer
          className="mt-3 pt-2"
          style={{
            borderTop: "1px solid var(--border-subtle)",
            fontSize: 11,
            color: "var(--fg-subtle)",
          }}
        >
          Source: InPost public press releases (annual reports 2022–2025). Live snapshots accumulating in TimescaleDB from May 2026.
        </footer>
      </article>
    </section>
  );
}

type TimelineTooltipProps = {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; color: string }>;
  label?: number;
};

function TimelineTooltip({ active, payload, label }: TimelineTooltipProps) {
  if (!active || !payload || payload.length === 0 || label == null) return null;
  return (
    <div
      style={{
        background: "var(--bg-surface-2)",
        border: "1px solid var(--border-default)",
        padding: "10px 12px",
        fontSize: 11.5,
        minWidth: 160,
      }}
    >
      <div
        className="mono"
        style={{ color: "var(--fg-subtle)", marginBottom: 6, fontSize: 10.5 }}
      >
        {formatTooltipDate(label)}
      </div>
      {payload
        .filter((p) => p.value != null)
        .sort((a, b) => b.value - a.value)
        .map((p) => (
          <div
            key={p.dataKey}
            className="flex items-center justify-between gap-4"
            style={{ color: "var(--fg-muted)" }}
          >
            <span className="inline-flex items-center gap-1.5">
              <i
                className="inline-block"
                style={{
                  width: 8,
                  height: 8,
                  background: p.color,
                  borderRadius: 1,
                }}
              />
              {p.dataKey}
            </span>
            <span
              className="mono"
              style={{ color: "var(--fg-default)" }}
            >
              {fmtInt(p.value)}
            </span>
          </div>
        ))}
    </div>
  );
}
