/**
 * API client root — configures hey-api's fetch client with the runtime base
 * URL and re-exports the generated SDK surface so consumers import a single
 * stable path: `@/lib/api`. Don't import from `./api/*.gen` directly; that
 * file regenerates with `pnpm codegen` and this re-export is the seam that
 * keeps callers stable across regens.
 */
import { client } from "./api/client.gen";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

client.setConfig({ baseUrl: API_BASE_URL });

export { client };
export * from "./api/sdk.gen";
export type * from "./api/types.gen";
