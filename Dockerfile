# syntax=docker/dockerfile:1.7

FROM node:24-bookworm-slim AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm AS runtime
LABEL org.opencontainers.image.title="SC4S Manager" \
      org.opencontainers.image.description="Private operator control plane for SC4S-compatible ingestion environments" \
      org.opencontainers.image.source="https://github.com/s6securitylabs/sc4s-manager" \
      org.opencontainers.image.licenses="Proprietary"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    SC4S_MANAGER_HOST=0.0.0.0 \
    SC4S_MANAGER_PORT=8090 \
    SC4S_ROOT=/opt/sc4s \
    SC4S_MANAGER_ROOT=/opt/sc4s-manager \
    SC4S_CONTROL_SOCKET=/run/sc4s-manager/control.sock

RUN addgroup --system --gid 10001 sc4s-manager \
    && adduser --system --uid 10001 --ingroup sc4s-manager --home /opt/sc4s-manager --no-create-home sc4s-manager \
    && mkdir -p /app/src /opt/sc4s/local /opt/sc4s/tls /opt/sc4s-manager/state /opt/sc4s-manager/backups /opt/sc4s-manager/templates /opt/sc4s-manager/packs /run/sc4s-manager \
    && chown -R sc4s-manager:sc4s-manager /opt/sc4s /opt/sc4s-manager /run/sc4s-manager

WORKDIR /app
COPY src/ /app/src/
COPY packs/ /opt/sc4s-manager/packs/
COPY --from=frontend-builder /build/frontend/dist/ /opt/sc4s-manager/frontend/dist/
COPY README.md LICENSE ./

USER sc4s-manager
EXPOSE 8090
VOLUME ["/opt/sc4s", "/opt/sc4s-manager", "/run/sc4s-manager"]
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=3).read().decode()); raise SystemExit(0 if data.get('status') == 'ok' else 1)"

CMD ["python", "/app/src/sc4s_manager/app.py"]
