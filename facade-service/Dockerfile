FROM python:3.10

WORKDIR /app
COPY . .

RUN pip install flask requests hazelcast-python-client psycopg2-binary

CMD ["python", "app.py"]