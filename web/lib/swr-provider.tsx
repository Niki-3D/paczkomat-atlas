/**
 * SWR global config — applied via app/layout.tsx.
 *
 * The dashboard's primary fetch is server-side in page.tsx, so SWR mostly
 * matters for any client-component refetches (none currently in scope, but
 * the provider is mounted up-front so adding them is friction-free). Focus
 * revalidation is off — the data updates once daily, no point hammering the
 * API every time someone tabs back. dedupe at 30s catches rapid re-renders.
 */
"use client";

import { SWRConfig } from "swr";

export function SwrProvider({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        revalidateOnFocus: false,
        revalidateIfStale: true,
        dedupingInterval: 30_000,
        errorRetryCount: 2,
      }}
    >
      {children}
    </SWRConfig>
  );
}
