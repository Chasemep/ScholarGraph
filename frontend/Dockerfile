# =============================================================================
# Stage 1: Build — Compile React 18 + Vite 5 production bundle
# =============================================================================
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# =============================================================================
# Stage 2: Runtime — Serve static bundle & reverse-proxy /api/ via Nginx
# =============================================================================
FROM nginx:stable-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

