FROM python:3.13.6-alpine@sha256:af1fd7a973d8adc761ee6b9d362b99329b39eb096ea3c53b8838f99bd187011e

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