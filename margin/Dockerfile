# Margin has no npm dependencies, so the image is just Node and the source.
FROM node:22-alpine

ENV NODE_ENV=production
WORKDIR /app
COPY package.json server.js ./
COPY lib ./lib
COPY public ./public
COPY scripts ./scripts

# The database, media and backups live in one volume.
RUN mkdir -p /app/data && chown -R node:node /app
USER node
VOLUME ["/app/data"]

ENV PORT=3000
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD wget -qO- http://127.0.0.1:3000/healthz || exit 1

# SIGTERM reaches node directly (no shell), so graceful shutdown works.
CMD ["node", "--no-warnings", "server.js"]
