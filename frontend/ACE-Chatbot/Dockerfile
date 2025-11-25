# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (peer deps for Angular 19)
RUN npm ci --legacy-peer-deps

# Copy source code
COPY . .

# Build the Angular app
RUN npm run build -- --configuration production --no-ssr

# Production stage
FROM nginx:alpine

# Copy built app to nginx (Angular outputs to dist/hotel-chatbot/browser)
COPY --from=build /app/dist/hotel-chatbot/browser /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
