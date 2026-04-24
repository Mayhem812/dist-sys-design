FROM python:3.10

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir flask requests hazelcast-python-client psycopg2-binary python-consul

CMD ["python", "app.py"]