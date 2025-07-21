FROM python:3.13.5-alpine@sha256:37b14db89f587f9eaa890e4a442a3fe55db452b69cca1403cc730bd0fbdc8aaf

RUN addgroup -S appgroup && adduser -S -G appgroup appuser

WORKDIR /app

COPY /app/ /app/app/
COPY version.txt requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt --require-hashes && \
    chown -R appuser:appgroup /app

ENV FLASK_APP=app.main.py:app \
    PYTHONUNBUFFERED=1 \
    REDIS_HOST=localhost \
    REDIS_PORT=6379 \
    CACHE_TTL=300

USER appuser

ENTRYPOINT [ "flask" ]
CMD [ "run", "--host=0.0.0.0" ]