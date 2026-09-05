FROM node:18-alpine AS builder
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
COPY frontend/ .

RUN npm ci
RUN npm run build

FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
