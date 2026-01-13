FROM python:3.13.7-alpine@sha256:9ba6d8cbebf0fb6546ae71f2a1c14f6ffd2fdab83af7fa5669734ef30ad48844

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
    MINIO_SECRET_KEY=minioadmin \
    REDIS_HOST=redis \
    MINIO_HOST=minio

USER appuser

ENTRYPOINT [ "flask" ]
CMD [ "run", "--host=0.0.0.0" ]