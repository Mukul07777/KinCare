# Dosely on Google Cloud Run: one container, one public port.
# Next.js serves the site on $PORT and forwards /api/* to the FastAPI app on 127.0.0.1:8000 inside the same container,
# so the session cookie stays first-party and no CORS is needed.
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
ENV KINCARE_API_URL=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1
RUN npm run build && npm prune --omit=dev

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TZ=Asia/Kolkata NODE_ENV=production \
    KINCARE_API_URL=http://127.0.0.1:8000 KINCARE_DB=/tmp/kincare/kincare.db COOKIE_SECURE=1
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 tzdata && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt
COPY api/ api/
COPY data/ data/
COPY --from=web /web /app/web
COPY cloudrun.sh /app/cloudrun.sh
RUN useradd -m kincare && mkdir -p /tmp/kincare && chown -R kincare /tmp/kincare /app/data
USER kincare
EXPOSE 8080
CMD ["bash", "/app/cloudrun.sh"]
