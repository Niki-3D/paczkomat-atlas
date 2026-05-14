import {
  type CountryKpi,
  type DensityGmina,
  type NetworkSummary,
  type Nuts2TopList,
  type VelocityPoint,
  getNetworkSummary,
  getVelocity,
  listCountryKpis,
  listGminy,
  topNuts2,
} from "@/lib/api";
import { CountryShare } from "@/components/dashboard/country-share";
import { DensityBars } from "@/components/dashboard/density-bars";
import { DensityMapIsland } from "@/components/dashboard/density-map-island";
import { Footer } from "@/components/dashboard/footer";
import { GminyTable } from "@/components/dashboard/gminy-table";
import { HeroKpis } from "@/components/dashboard/hero-kpis";
import { Nav } from "@/components/dashboard/nav";
import { VelocityTimeline } from "@/components/dashboard/velocity-timeline";

export const revalidate = 300; // refetch at most every 5 minutes

type ProbeResult = {
  ok: boolean;
  latencyMs: number | null;
  lockerCount: number | null;
};

async function probeHealth(): Promise<ProbeResult> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
  const start = Date.now();
  try {
    const res = await fetch(`${base}/api/v1/health`, { cache: "no-store" });
    const latencyMs = Date.now() - start;
    if (!res.ok) return { ok: false, latencyMs, lockerCount: null };
    const body = (await res.json()) as {
      status?: string;
      locker_count?: number;
    };
    return {
      ok: body.status === "ok",
      latencyMs,
      lockerCount: body.locker_count ?? null,
    };
  } catch {
    return { ok: false, latencyMs: null, lockerCount: null };
  }
}

type Bundle = {
  summary: NetworkSummary | null;
  countries: CountryKpi[];
  topNuts2Rows: Nuts2TopList[];
  velocity: VelocityPoint[];
  gminy: DensityGmina[];
  health: ProbeResult;
};

// Backend hits an asyncpg/pgbouncer prepared-statement collision under
// concurrent load (a known interaction with pool_pre_ping). Retry the
// SDK call up to MAX_TRIES times with jittered backoff so transient
// 500s self-heal before we paint an error panel.
const MAX_TRIES = 4;

async function withRetry<T>(
  label: string,
  fn: () => Promise<T>,
  ok: (r: T) => boolean,
): Promise<T> {
  let result = await fn();
  for (let attempt = 2; attempt <= MAX_TRIES; attempt++) {
    if (ok(result)) return result;
    await new Promise((r) => setTimeout(r, 60 * attempt + Math.random() * 80));
    result = await fn();
  }
  if (!ok(result)) console.warn(`[loadAll] ${label} failed ${MAX_TRIES}x`);
  return result;
}

const isOk = <T extends { data?: unknown; error?: unknown }>(r: T): boolean =>
  Boolean(r?.data) && !r?.error;

async function loadAll(): Promise<Bundle> {
  const [
    healthRes,
    summaryRes,
    countriesRes,
    topNuts2Res,
    velocityRes,
    gminyRes,
  ] = await Promise.allSettled([
    probeHealth(),
    withRetry("summary", () => getNetworkSummary(), isOk),
    withRetry("countries", () => listCountryKpis(), isOk),
    withRetry("topNuts2", () => topNuts2({ query: { limit: 15 } }), isOk),
    withRetry("velocity", () => getVelocity(), isOk),
    // 2500 covers all gminy with population matched (~2422)
    withRetry(
      "gminy",
      () => listGminy({ query: { limit: 2500, min_population: 0 } }),
      isOk,
    ),
  ]);

  return {
    summary:
      summaryRes.status === "fulfilled" && summaryRes.value.data
        ? summaryRes.value.data.data
        : null,
    countries:
      countriesRes.status === "fulfilled" && countriesRes.value.data
        ? countriesRes.value.data.data
        : [],
    topNuts2Rows:
      topNuts2Res.status === "fulfilled" && topNuts2Res.value.data
        ? topNuts2Res.value.data.data
        : [],
    velocity:
      velocityRes.status === "fulfilled" && velocityRes.value.data
        ? velocityRes.value.data.data
        : [],
    gminy:
      gminyRes.status === "fulfilled" && gminyRes.value.data
        ? gminyRes.value.data.data
        : [],
    health:
      healthRes.status === "fulfilled"
        ? healthRes.value
        : { ok: false, latencyMs: null, lockerCount: null },
  };
}

export default async function HomePage() {
  const data = await loadAll();

  return (
    <>
      <Nav apiOk={data.health.ok} apiLatencyMs={data.health.latencyMs} />
      <main
        className="mx-auto flex flex-col px-6 pb-12 pt-6 gap-7"
        style={{ maxWidth: 1480 }}
      >
        {data.summary ? (
          <HeroKpis
            summary={data.summary}
            countryKpis={data.countries}
            topNuts2={data.topNuts2Rows}
          />
        ) : (
          <ErrorPanel
            title="Hero KPIs unavailable"
            detail="Could not load /api/v1/kpi/summary."
          />
        )}

        <section
          className="grid gap-3.5"
          style={{ gridTemplateColumns: "minmax(0, 6fr) minmax(0, 4fr)" }}
        >
          <DensityMapIsland />
          {data.topNuts2Rows.length > 0 ? (
            <DensityBars rows={data.topNuts2Rows} />
          ) : (
            <ErrorPanel
              title="Density bars unavailable"
              detail="Could not load /api/v1/density/nuts2/top."
            />
          )}
        </section>

        {data.countries.length > 0 ? (
          <CountryShare rows={data.countries} />
        ) : (
          <ErrorPanel
            title="Country composition unavailable"
            detail="Could not load /api/v1/kpi/countries."
          />
        )}

        {data.velocity.length > 0 ? (
          <VelocityTimeline points={data.velocity} />
        ) : (
          <ErrorPanel
            title="Velocity timeline unavailable"
            detail="Could not load /api/v1/velocity."
          />
        )}

        {data.gminy.length > 0 ? (
          <GminyTable rows={data.gminy} />
        ) : (
          <ErrorPanel
            title="Gminy deep-dive unavailable"
            detail="Could not load /api/v1/density/gminy."
          />
        )}

        <Footer totalRecords={data.health.lockerCount} />
      </main>
    </>
  );
}

function ErrorPanel({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <article
      className="panel flex flex-col gap-2 px-6 py-6"
      style={{ minHeight: 120 }}
    >
      <div className="panel-title">{title}</div>
      <div className="panel-sub">{detail}</div>
      <div
        className="mono mt-2"
        style={{ fontSize: 11, color: "var(--fg-subtle)" }}
      >
        check{" "}
        <a
          href="http://localhost:8080/api/v1/health"
          target="_blank"
          rel="noreferrer"
          style={{
            color: "var(--accent)",
            borderBottom: "1px dashed var(--accent-lo)",
          }}
        >
          /api/v1/health
        </a>{" "}
        — backend may be down or unreachable.
      </div>
    </article>
  );
}
