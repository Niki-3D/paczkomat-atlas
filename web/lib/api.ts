import { client } from "./api/client.gen";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

client.setConfig({ baseUrl: API_BASE_URL });

export { client };
export * from "./api/sdk.gen";
export type * from "./api/types.gen";
