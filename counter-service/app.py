from flask import Flask, jsonify
import psycopg2
import time
import os
import hazelcast
import threading
import consul
import json
import uuid

app = Flask(__name__)

CONSUL_HOST = "consul"
CONSUL_PORT = 8500


c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


def register():
    service_id = f"counter-{uuid.uuid4()}"

    while True:
        try:
            c.agent.service.register(
                name="counter-service",
                service_id=service_id,
                address="counter-service",
                port=5002,
                check={
                    "http": "http://counter-service:5002/health",
                    "interval": "5s",
                    "timeout": "2s"
                }
            )
            print("Registered in Consul")
            break
        except Exception as e:
            print("Consul not ready, retrying...", e)
            time.sleep(2)

register()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def load_queue_config():
    while True:
        try:
            _, data = c.kv.get("queue/config")

            if data is None:
                raise Exception("Queue config not found yet")

            config = json.loads(data["Value"])
            print("Queue config loaded:", config)
            return config

        except Exception as e:
            print("Waiting for queue config...", e)
            time.sleep(2)

queue_config = load_queue_config()
queue_name = queue_config["name"]


conn = None

for i in range(50):
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        conn.autocommit = True
        print("Connected to PostgreSQL")
        break
    except Exception as e:
        print("Waiting for DB...", e)
        time.sleep(2)

if conn is None:
    raise Exception("DB connection failed")


with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            user_id TEXT PRIMARY KEY,
            balance INT NOT NULL
        )
    """)


client = None
for i in range(10):
    try:
        client = hazelcast.HazelcastClient(
            cluster_name="dev-cluster",
            cluster_members=[
                "hazelcast1:5701",
                "hazelcast2:5701",
                "hazelcast3:5701"
            ]
        )
        print("Connected to Hazelcast")
        break
    except Exception as e:
        print("Waiting for Hazelcast...", e)
        time.sleep(2)

if client is None:
    raise Exception("Hazelcast connection failed")

queue = client.get_queue(queue_name).blocking()


total_counter_time = 0.0


def consume():
    global total_counter_time

    print("Queue consumer started")

    while True:
        try:
            data = queue.take()

            t = time.time()

            user_id = data["user_id"]
            amount = data["amount"]

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO accounts (user_id, balance)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET balance = accounts.balance + EXCLUDED.balance
                """, (user_id, amount))

            total_counter_time += (time.time() - t)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(1)

threading.Thread(target=consume, daemon=True).start()


@app.route("/balances", methods=["GET"])
def balances():
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, balance FROM accounts")
        rows = cur.fetchall()

    return jsonify({r[0]: r[1] for r in rows})


@app.route("/metrics", methods=["GET"])
def metrics():
    return jsonify({
        "total_counter_time": total_counter_time
    })

app.run(host="0.0.0.0", port=5002, threaded=True)