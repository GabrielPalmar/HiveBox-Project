FROM python:3.15.0b1-alpine@sha256:8fe37a98f64ee15fee985b1536cc005aef67847c31f435772250165307a68c2e

RUN addgroup -S appgroup && adduser -S -G appgroup appuser

WORKDIR /app

COPY /app/ /app/app/
COPY version.txt requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt --require-hashes && \
    chown -R appuser:appgroup /app

ENV FLASK_APP=app.main:app \
    PYTHONUNBUFFERED=1 \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    CACHE_TTL=300 \
    MINIO_PORT=9000 \
    REDIS_HOST=redis \
    MINIO_HOST=minio

USER appuser

ENTRYPOINT [ "flask" ]
CMD [ "run", "--host=0.0.0.0" ]