# Build stage
FROM mambaorg/micromamba:1.5-jammy AS build

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN eval "$(micromamba shell hook --shell=bash)" && micromamba activate base && \
    npm ci

COPY frontend/ ./
RUN eval "$(micromamba shell hook --shell=bash)" && micromamba activate base && \
    npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
