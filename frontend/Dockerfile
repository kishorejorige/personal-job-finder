# Stage 1: Build Angular application
FROM node:22-alpine AS build

WORKDIR /app

# Copy package descriptors
COPY package*.json /app/

# Install dependencies
RUN npm ci

# Copy source code and build
COPY . /app/
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:alpine

# Copy built browser assets
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
