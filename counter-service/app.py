from flask import Flask, jsonify
import psycopg2
import time
import os
import hazelcast
import threading
import requests

app = Flask(__name__)

CONFIG_URL = "http://config-server:5003"


def register():
    while True:
        try:
            requests.post(f"{CONFIG_URL}/register", json={
                "name": "counter-service",
                "url": "http://counter-service:5002"
            })
            print("Registered in config-server")
            break
        except:
            time.sleep(2)

register()


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


client = hazelcast.HazelcastClient(
    cluster_name="dev-cluster",
    cluster_members=[
        "hazelcast1:5701",
        "hazelcast2:5701",
        "hazelcast3:5701"
    ]
)

queue = client.get_queue("transactions-queue").blocking()

def consume():
    print("Queue consumer started")
    while True:
        try:
            data = queue.take()

            user_id = data["user_id"]
            amount = data["amount"]

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO accounts (user_id, balance)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET balance = accounts.balance + EXCLUDED.balance
                """, (user_id, amount))

            print("PROCESSED:", user_id, amount)

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

app.run(host="0.0.0.0", port=5002, threaded=True)