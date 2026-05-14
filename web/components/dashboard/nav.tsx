"use client";

import { Github } from "lucide-react";
import { useState } from "react";

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
            <Github size={16} />
          </a>
        </div>
      </div>
    </header>
  );
}
