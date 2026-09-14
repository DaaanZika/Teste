# Multi-stage build: the "dev" stage runs the Vite dev server (hot reload,
# used by docker-compose.yml); "production" builds the static bundle and
# serves it with nginx (used by docker-compose.prod.yml). Same file for
# both — no separate Dockerfile.dev / Dockerfile.prod to keep in sync.

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- dev: hot-reloading Vite dev server, source mounted as a volume ---
FROM deps AS dev
WORKDIR /app
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# --- build: produces the static bundle for the production stage ---
FROM deps AS build
WORKDIR /app
COPY . .
# Baked in at build time — Vite inlines VITE_* vars into the bundle.
# Override with --build-arg for a real deployment domain.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# --- production: static files behind nginx, SPA routing fallback ---
FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
