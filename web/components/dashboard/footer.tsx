/**
 * Page footer — data sources, caveats, repo links.
 *
 * `totalRecords` comes from the /health probe (live count of rows in the
 * lockers table). Caveats are static disclosures that match what the data
 * actually supports: GB outside the NUTS-2 view, pre-launch Nordic markets,
 * PRG boundary vintage. Operational links use same-origin relative paths so
 * they resolve to whichever host Caddy is serving from (localhost in dev,
 * the public IP / hostname in prod).
 */
type FooterProps = {
  totalRecords: number | null;
};

export function Footer({ totalRecords }: FooterProps) {
  return (
    <footer
      className="mt-6 pt-6"
      style={{ borderTop: "1px solid var(--border-subtle)" }}
    >
      <div className="footer-grid-row grid gap-8 mb-6 grid-cols-1 sm:grid-cols-2 lg:[grid-template-columns:1.4fr_1fr_1.4fr_0.8fr]">
        <div>
          <FootTitle>Paczkomat Atlas</FootTitle>
          <p style={{ fontSize: 12, color: "var(--fg-muted)" }}>
            Single-page analytics on the InPost public network. Read-only, daily refresh.
          </p>
        </div>
        <div>
          <FootTitle>Data sources</FootTitle>
          <FootList>
            <li>
              InPost public API{" "}
              <span className="mono">
                · {totalRecords != null ? totalRecords.toLocaleString("en-US") : "—"} records
              </span>
            </li>
            <li>PRG gminy shapefile <span className="mono">· 2022-06-27</span></li>
            <li>Eurostat NUTS-2 <span className="mono">· 2024</span></li>
            <li>GUS BDL gmina population <span className="mono">· 2024</span></li>
          </FootList>
        </div>
        <div>
          <FootTitle>Caveats</FootTitle>
          <FootList>
            <li>PRG vintage 2022 — micro-boundary changes don&apos;t affect 10k-resolution math.</li>
            <li>GB excluded from NUTS-2 view (Eurostat dropped UK post-Brexit). Still in country KPIs.</li>
            <li>SE / DK / FI rendered as pre-launch — catalog rows exist but zero operational lockers.</li>
          </FootList>
        </div>
        <div>
          <FootTitle>Links</FootTitle>
          <FootList>
            <li><FootLink href="https://github.com/Niki-3D/paczkomat-atlas">GitHub repository →</FootLink></li>
            <li><FootLink href="https://github.com/Niki-3D/paczkomat-atlas/blob/main/JOURNEY.md">Build journey →</FootLink></li>
            <li><FootLink href="/docs">API documentation →</FootLink></li>
          </FootList>
        </div>
      </div>
      <div
        className="py-3"
        style={{
          fontSize: 11,
          color: "var(--fg-subtle)",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        InPost Technology Internship 2026 submission · Built by Nikodem Brożyniak
      </div>
    </footer>
  );
}

function FootTitle({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="uppercase mb-2.5"
      style={{
        fontSize: 11,
        letterSpacing: "0.08em",
        color: "var(--fg-default)",
      }}
    >
      {children}
    </div>
  );
}

function FootList({ children }: { children: React.ReactNode }) {
  return (
    <ul
      className="list-none p-0 m-0 flex flex-col gap-1.5"
      style={{ fontSize: 11.5, color: "var(--fg-muted)" }}
    >
      {children}
    </ul>
  );
}

function FootLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="transition-colors"
      style={{
        color: "var(--fg-muted)",
        borderBottom: "1px dashed var(--border-strong)",
      }}
    >
      {children}
    </a>
  );
}
