FROM node:22-alpine AS base
WORKDIR /app

# Dev stage
FROM base AS dev
EXPOSE 3000
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]

# Build stage
FROM base AS build
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM base AS production
COPY --from=build /app/.output /app/.output
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]