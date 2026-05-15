import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the production Dockerfile — bundles a minimal Node.js
  // server.js + only the deps the app uses, so the runtime image stays small.
  output: "standalone",
};

export default nextConfig;
