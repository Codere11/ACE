# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy source code
COPY . .

# Build the Angular app (disable SSR for Docker)
RUN npm run build -- --configuration production --no-ssr

# Production stage
FROM nginx:alpine

# Copy built app to nginx (Angular outputs to dist/manager-dashboard/browser)
COPY --from=build /app/dist/manager-dashboard/browser /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
