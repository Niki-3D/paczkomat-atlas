# Next.js production image — multi-stage build with the "standalone" output.
# Build context MUST be the repo root (pnpm workspace lockfile lives there).
# Final image runs `node server.js` and contains only the deps the app uses.
FROM node:22-alpine AS base
RUN corepack enable

FROM base AS deps
WORKDIR /repo
# Workspace-aware install: copy the root manifest + lockfile + workspace
# config, then the workspace package.json, then run a frozen install. This
# matches what `pnpm install` does at repo root and keeps the lockfile honest.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY web/package.json ./web/package.json
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/web/node_modules ./web/node_modules
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY web ./web
ENV NEXT_TELEMETRY_DISABLED=1
# NEXT_PUBLIC_API_BASE_URL must be present at BUILD TIME for Next.js to
# inline it into the client bundle. Pass via compose build args.
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
WORKDIR /repo/web
RUN pnpm build

FROM base AS production
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# `output: "standalone"` (in next.config.ts) emits a self-contained server
# bundle under web/.next/standalone — copy that plus the static assets.
# Standalone preserves workspace structure: server.js lives under web/.
COPY --from=builder /repo/web/.next/standalone ./
COPY --from=builder /repo/web/.next/static ./web/.next/static
COPY --from=builder /repo/web/public ./web/public
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
WORKDIR /app/web
CMD ["node", "server.js"]
