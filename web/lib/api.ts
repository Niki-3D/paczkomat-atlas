/**
 * API client root — configures hey-api's fetch client with the runtime base
 * URL and re-exports the generated SDK surface so consumers import a single
 * stable path: `@/lib/api`. Don't import from `./api/*.gen` directly; that
 * file regenerates with `pnpm codegen` and this re-export is the seam that
 * keeps callers stable across regens.
 *
 * Two URLs, two contexts:
 *
 * - Browser bundle: NEXT_PUBLIC_API_BASE_URL is inlined into the JS that
 *   ships to the client at BUILD time. Must be the public origin.
 *
 * - Server / SSR: process.env reads happen at runtime. Server components
 *   should reach the API via the internal docker hostname (api:8000) so
 *   requests stay on the docker network and don't loop back out through
 *   Caddy. INTERNAL_API_BASE_URL is set in the prod compose; we fall back
 *   to NEXT_PUBLIC for dev where everything runs on localhost.
 */
import { client } from "./api/client.gen";

// On the server `typeof window === "undefined"`. Tree-shaking removes the
// server branch from the client bundle, so INTERNAL_API_BASE_URL is never
// shipped to browsers even if it's set.
export const API_BASE_URL =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_BASE_URL ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      "http://localhost:8080"
    : process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

client.setConfig({ baseUrl: API_BASE_URL });

export { client };
export * from "./api/sdk.gen";
export type * from "./api/types.gen";
