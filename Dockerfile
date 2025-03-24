FROM python:3.13.2-alpine@sha256:323a717dc4a010fee21e3f1aac738ee10bb485de4e7593ce242b36ee48d6b352

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