FROM python:3.9.23-alpine@sha256:372f3cfc1738ed91b64c7d36a7a02d5c3468ec1f60c906872c3fd346dda8cbbb

RUN addgroup -S appgroup && adduser -S -G appgroup appuser

WORKDIR /app

COPY /app/ /app/app/
COPY version.txt requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt --require-hashes && \
    chown -R appuser:appgroup /app

ENV FLASK_APP=app.main.py:app \
    PYTHONUNBUFFERED=1 \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    CACHE_TTL=300 \
    MINIO_PORT=9000 \
    MINIO_ACCESS_KEY=minioadmin \
    MINIO_SECRET_KEY=minioadmin

USER appuser

ENTRYPOINT [ "flask" ]
CMD [ "run", "--host=0.0.0.0" ]