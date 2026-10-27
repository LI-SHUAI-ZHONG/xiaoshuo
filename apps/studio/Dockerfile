# syntax=docker/dockerfile:1.7

FROM node:22.23.2-bookworm-slim AS builder

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@11.25.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/studio/package.json apps/studio/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/ui/package.json packages/ui/package.json

RUN pnpm install --frozen-lockfile

COPY tsconfig.json ./
COPY apps/studio apps/studio
COPY packages/api-client packages/api-client
COPY packages/ui packages/ui

ARG ACCOS_API_ORIGIN=http://api:8000
ENV ACCOS_API_ORIGIN=${ACCOS_API_ORIGIN}

RUN pnpm --filter @accos/studio run build

FROM node:22.23.2-bookworm-slim AS runtime

ARG ACCOS_VERSION=0.1.0-skeleton
ARG ACCOS_REVISION=unknown

LABEL org.opencontainers.image.title="ACCOS Studio" \
      org.opencontainers.image.description="ACCOS creator Studio skeleton runtime" \
      org.opencontainers.image.version="${ACCOS_VERSION}" \
      org.opencontainers.image.revision="${ACCOS_REVISION}" \
      org.opencontainers.image.source="https://invalid.local/accos" \
      org.opencontainers.image.licenses="Proprietary"

ENV HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    PORT=3000

RUN groupadd --system --gid 10001 accos \
    && useradd --system --uid 10001 --gid accos --home-dir /nonexistent --shell /usr/sbin/nologin accos

WORKDIR /app

COPY --from=builder --chown=accos:accos /app/apps/studio/.next/standalone ./
COPY --from=builder --chown=accos:accos /app/apps/studio/.next/static /app/apps/studio/.next/static
COPY --from=builder --chown=accos:accos /app/pnpm-lock.yaml /app/dependency-manifests/pnpm-lock.yaml

USER 10001:10001

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=6 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/status').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]

CMD ["node", "apps/studio/server.js"]

