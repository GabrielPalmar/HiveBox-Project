FROM python:3.13.4-alpine@sha256:b4d299311845147e7e47c970566906caf8378a1f04e5d3de65b5f2e834f8e3bf

RUN addgroup -S appgroup && adduser -S -G appgroup appuser

WORKDIR /app

COPY main.py opensense.py version.txt requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt --require-hashes && \
    chown -R appuser:appgroup /app

ENV FLASK_APP=main.py \
    PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT [ "flask" ]
CMD [ "run", "--host=0.0.0.0" ]