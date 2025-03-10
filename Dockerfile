FROM python:3.12-alpine

COPY main.py /app/main.py
COPY opensense.py /app/opensense.py
COPY version.txt /app/version.txt
COPY requirements.txt /requirements.txt

WORKDIR /app

RUN pip install --no-cache-dir -r /requirements.txt

ENV FLASK_APP=main.py

ENTRYPOINT [ "flask" ]
CMD [ "run", "--host=0.0.0.0" ]