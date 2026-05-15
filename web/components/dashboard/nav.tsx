/**
 * Top navigation bar — branding, scope toggle (PL/EU), API status pill.
 *
 * Scope toggle dispatches a `pa:scope` window CustomEvent that DensityMap
 * listens to and flies the camera in response. Keeping it event-based
 * (instead of prop-drilling) avoids forcing the dashboard page into a
 * client component just to share state with the map.
 *
 * Status pill colors come from --success / --danger; the green/red glow
 * rings around the dot use box-shadow with derived RGBA values
 * (acceptable per design-tokens.md — boxShadow is allowed on non-card
 * elements like status indicators).
 */
"use client";

import { useState } from "react";

function GithubMark() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.92.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.52-1.32-1.28-1.67-1.28-1.67-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.74.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.47.11-3.06 0 0 .97-.31 3.18 1.18.92-.26 1.91-.39 2.89-.39s1.97.13 2.89.39c2.21-1.49 3.18-1.18 3.18-1.18.63 1.59.23 2.77.11 3.06.74.81 1.19 1.84 1.19 3.1 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.13v3.16c0 .31.21.66.79.55C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5z" />
    </svg>
  );
}

type Scope = "PL" | "EU";

export function Nav({
  apiLatencyMs,
  apiOk,
}: {
  apiLatencyMs: number | null;
  apiOk: boolean;
}) {
  const [scope, setScope] = useState<Scope>("PL");

  function onScope(next: Scope): void {
    setScope(next);
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent<{ scope: Scope }>("pa:scope", { detail: { scope: next } }),
      );
    }
  }

  return (
    <header
      className="sticky top-0 z-40 backdrop-blur-md"
      style={{
        background: "rgba(10, 10, 11, 0.86)",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div className="mx-auto flex h-14 items-center justify-between gap-6 px-6" style={{ maxWidth: 1480 }}>
        <div className="flex items-center gap-3">
          <div
            className="grid place-items-center"
            style={{
              width: 28,
              height: 28,
              color: "var(--accent)",
              background: "var(--bg-surface-1)",
              border: "1px solid var(--border-default)",
            }}
          >
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden>
              <rect x="2" y="6" width="9" height="5" rx="0.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
              <rect x="2" y="13" width="9" height="5" rx="0.5" fill="currentColor" />
              <rect x="13" y="6" width="9" height="5" rx="0.5" fill="currentColor" />
              <rect x="13" y="13" width="9" height="5" rx="0.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
            </svg>
          </div>
          <div className="leading-tight">
            <div
              className="whitespace-nowrap"
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 17,
                fontWeight: 400,
                letterSpacing: "-0.018em",
                lineHeight: 1,
              }}
            >
              Paczkomat Atlas
            </div>
            <div
              className="mt-1 whitespace-nowrap"
              style={{ fontSize: 10.5, color: "var(--fg-muted)", lineHeight: 1 }}
            >
              InPost network analytics
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div
            role="tablist"
            aria-label="Scope"
            className="inline-flex overflow-hidden"
            style={{
              border: "1px solid var(--border-default)",
              background: "var(--bg-surface-1)",
            }}
          >
            {(["PL", "EU"] as const).map((s, i) => (
              <button
                key={s}
                role="tab"
                aria-selected={scope === s}
                onClick={() => onScope(s)}
                className="mono transition-colors"
                style={{
                  padding: "5px 12px",
                  fontSize: 12,
                  color: scope === s ? "var(--accent)" : "var(--fg-muted)",
                  background: scope === s ? "var(--bg-surface-3)" : "transparent",
                  borderRight: i === 0 ? "1px solid var(--border-default)" : "none",
                }}
              >
                {s}
              </button>
            ))}
          </div>

          <div className="mono flex items-center gap-2" style={{ fontSize: 12, color: "var(--fg-muted)" }}>
            <span
              aria-hidden
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: apiOk ? "var(--success)" : "var(--danger)",
                boxShadow: apiOk
                  ? "0 0 0 3px rgba(52, 211, 153, 0.12)"
                  : "0 0 0 3px rgba(248, 113, 113, 0.12)",
              }}
            />
            <span>
              api {apiOk ? "ok" : "down"}
              {apiLatencyMs != null && (
                <>
                  {" · "}
                  <span className="mono">{apiLatencyMs} ms</span>
                </>
              )}
            </span>
          </div>

          <a
            href="https://github.com/Niki-3D/paczkomat-atlas"
            target="_blank"
            rel="noreferrer"
            aria-label="GitHub"
            title="GitHub"
            className="grid place-items-center transition-colors"
            style={{
              width: 28,
              height: 28,
              color: "var(--fg-muted)",
              background: "var(--bg-surface-1)",
              border: "1px solid var(--border-default)",
            }}
          >
            <GithubMark />
          </a>
        </div>
      </div>
    </header>
  );
}
