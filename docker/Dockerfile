FROM python:3.13.1-alpine@sha256:f9d772b2b40910ee8de2ac2b15ff740b5f26b37fc811f6ada28fce71a2542b0e

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