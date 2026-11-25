# ---- snip web image: build React, then serve it with nginx ----

# Stage 1: build the static files
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: tiny nginx image that only contains the built files
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Vite built with base "/app/", so the files must live in an "app" folder
COPY --from=build /app/dist /usr/share/nginx/html/app
EXPOSE 80
