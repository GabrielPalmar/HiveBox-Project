FROM python:3.12-alpine

COPY version.txt /app/version.txt
COPY print_version.py /app/print_version.py

WORKDIR /app

CMD ["python", "print_version.py"]