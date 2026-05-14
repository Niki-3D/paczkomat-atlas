import type { CountryKpi, NetworkSummary, Nuts2TopList } from "@/lib/api";
import { fmt1, fmt2, fmtInt } from "@/lib/format";

type HeroProps = {
  summary: NetworkSummary;
  countryKpis: CountryKpi[];
  topNuts2: Nuts2TopList[];
};

export function HeroKpis({ summary, countryKpis, topNuts2 }: HeroProps) {
  const lockerShare =
    summary.n_network_total > 0
      ? (summary.n_lockers_total / summary.n_network_total) * 100
      : 0;
  const pudoShare = 100 - lockerShare;

  const pl = countryKpis.find((c) => c.country === "PL");
  const pl247 = pl?.n_247 ?? 0;

  const topPl = topNuts2.find((r) => r.country === "PL");
  const topNonPl = topNuts2.find((r) => r.country !== "PL");
  const ratio =
    topPl && topNonPl && topNonPl.lockers_per_10k > 0
      ? topPl.lockers_per_10k / topNonPl.lockers_per_10k
      : null;

  return (
    <section className="grid gap-3.5" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
      <KpiCard
        label="Pickup points network"
        tag="live · mv_country_kpi"
        value={fmtInt(summary.n_network_total)}
        subline={
          <>
            <span><span style={{ color: "var(--accent)" }}>{summary.n_countries_active}</span> active countries</span>
            <Sep />
            <span><span className="mono">{fmtInt(summary.n_lockers_total)}</span> lockers</span>
            <Sep />
            <span><span className="mono">{fmtInt(summary.n_pudo_total)}</span> PUDO</span>
          </>
        }
      >
        <Stackbar lockerPct={lockerShare} />
        <div className="flex flex-wrap gap-x-4" style={{ fontSize: 11.5, color: "var(--fg-muted)" }}>
          <span><Swatch tone="amber" /> lockers <span className="mono">{fmt1(lockerShare)}%</span></span>
          <span><Swatch tone="subtle" /> PUDO partners <span className="mono">{fmt1(pudoShare)}%</span></span>
        </div>
      </KpiCard>

      <KpiCard
        label="Polish lockers"
        tag="country = PL"
        value={fmtInt(pl?.n_lockers ?? 0)}
        subline={
          <>
            <span>
              <span className="mono" style={{ color: "var(--accent)" }}>
                {fmt1(pl?.pct_247 ?? null)}%
              </span>{" "}
              open 24/7
            </span>
            <Sep />
            <span><span className="mono">{fmtInt(pl247)}</span> always-on</span>
          </>
        }
      >
        <DotGrid pct={pl?.pct_247 ?? 0} />
        <div className="flex flex-wrap gap-x-4" style={{ fontSize: 11.5, color: "var(--fg-muted)" }}>
          <span><Swatch tone="amber" /> 24/7 access</span>
          <span><Swatch tone="subtle" /> business hours</span>
        </div>
      </KpiCard>

      <KpiCard
        label="Density vs rest of EU"
        tag="lockers / 10k"
        value={
          <>
            {ratio != null ? fmt1(ratio) : "—"}
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 34,
                color: "var(--accent)",
                marginLeft: 2,
                fontWeight: 300,
                fontStyle: "italic",
                letterSpacing: "-0.02em",
              }}
            >
              ×
            </span>
          </>
        }
        subline={
          <span>
            Poland is{" "}
            <span style={{ color: "var(--accent)" }}>
              {ratio != null ? fmt2(ratio) : "—"}×
            </span>{" "}
            denser than the densest non-PL EU region
          </span>
        }
      >
        {topPl && topNonPl && (
          <div className="flex flex-col gap-1.5">
            <VsRow
              label={`${topPl.name_latn} · ${topPl.country}`}
              value={fmt2(topPl.lockers_per_10k)}
              widthPct={100}
            />
            <VsRow
              label={`${topNonPl.name_latn} · ${topNonPl.country}`}
              value={fmt2(topNonPl.lockers_per_10k)}
              widthPct={(topNonPl.lockers_per_10k / topPl.lockers_per_10k) * 100}
              muted
            />
          </div>
        )}
      </KpiCard>
    </section>
  );
}

function KpiCard({
  label,
  tag,
  value,
  subline,
  children,
}: {
  label: string;
  tag: string;
  value: React.ReactNode;
  subline: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <article
      className="flex flex-col"
      style={{
        background: "var(--bg-surface-1)",
        border: "1px solid var(--border-subtle)",
        padding: "20px 22px",
        minHeight: 180,
      }}
    >
      <header className="mb-3.5 flex items-center justify-between">
        <span
          className="uppercase"
          style={{ fontSize: 11, color: "var(--fg-muted)", letterSpacing: "0.06em" }}
        >
          {label}
        </span>
        <span
          className="mono"
          style={{
            fontSize: 10.5,
            color: "var(--fg-subtle)",
            padding: "2px 6px",
            border: "1px solid var(--border-subtle)",
          }}
        >
          {tag}
        </span>
      </header>
      <div
        className="mono"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 60,
          fontWeight: 300,
          letterSpacing: "-0.035em",
          lineHeight: 0.95,
          color: "var(--fg-default)",
          marginBottom: 10,
          fontVariantNumeric: "tabular-nums lining-nums",
        }}
      >
        {value}
      </div>
      <div className="flex flex-wrap items-center gap-x-1" style={{ fontSize: 12.5, color: "var(--fg-muted)" }}>
        {subline}
      </div>
      <div className="mt-auto pt-3.5 flex flex-col gap-2">{children}</div>
    </article>
  );
}

function Sep() {
  return <span style={{ color: "var(--border-strong)", margin: "0 0.25em" }}>·</span>;
}

function Swatch({ tone }: { tone: "amber" | "subtle" }) {
  return (
    <i
      className="inline-block align-[-1px] mr-1.5"
      style={{
        width: 9,
        height: 9,
        background: tone === "amber" ? "var(--accent)" : "var(--bg-surface-3)",
        border: tone === "amber" ? "none" : "1px solid var(--border-default)",
      }}
    />
  );
}

function Stackbar({ lockerPct }: { lockerPct: number }) {
  return (
    <div
      className="overflow-hidden relative"
      style={{ height: 6, background: "var(--bg-surface-3)" }}
    >
      <div style={{ height: "100%", width: `${lockerPct}%`, background: "var(--accent)" }} />
    </div>
  );
}

function DotGrid({ pct }: { pct: number }) {
  const on = Math.round((pct / 100) * 100);
  return (
    <div
      className="grid gap-[2px]"
      style={{ gridTemplateColumns: "repeat(25, 1fr)", height: 28 }}
      aria-label={`${pct.toFixed(1)}% of 100 squares filled`}
    >
      {Array.from({ length: 100 }, (_, i) => (
        <i
          key={i}
          className="block"
          style={{
            background: i < on ? "var(--accent)" : "var(--bg-surface-3)",
          }}
        />
      ))}
    </div>
  );
}

function VsRow({
  label,
  value,
  widthPct,
  muted = false,
}: {
  label: string;
  value: string;
  widthPct: number;
  muted?: boolean;
}) {
  return (
    <div
      className="grid items-center gap-2.5"
      style={{ gridTemplateColumns: "130px 1fr 48px", fontSize: 11.5 }}
    >
      <div style={{ color: "var(--fg-muted)" }}>{label}</div>
      <div className="overflow-hidden" style={{ height: 6, background: "var(--bg-surface-3)" }}>
        <div
          style={{
            height: "100%",
            width: `${Math.min(100, widthPct)}%`,
            background: muted ? "var(--accent-lo)" : "var(--accent)",
          }}
        />
      </div>
      <div
        className="text-right mono"
        style={{ fontSize: 12, color: "var(--fg-default)" }}
      >
        {value}
      </div>
    </div>
  );
}
