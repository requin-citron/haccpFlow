FROM node:22-alpine AS deps
WORKDIR /app
# The image already ships a yarn shim through corepack; packageManager in
# package.json pins the exact version (1.22.22, same as the developer machine).
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --non-interactive

# Development target: the source is bind-mounted by docker compose, so code
# changes are picked up by Next.js hot reload without rebuilding the image.
FROM deps AS development
COPY . .
EXPOSE 3000
CMD ["yarn", "dev"]

FROM node:22-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN yarn build

FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
