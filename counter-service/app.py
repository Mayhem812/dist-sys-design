from flask import Flask, request, jsonify
import psycopg2
import time
import os

app = Flask(__name__)

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


@app.route("/update", methods=["POST"])
def update():
    data = request.json
    user_id = data["user_id"]
    amount = data["amount"]

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO accounts (user_id, balance)
            VALUES (%s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET balance = accounts.balance + EXCLUDED.balance
            RETURNING balance
        """, (user_id, amount))

        balance = cur.fetchone()[0]

    print("UPDATED:", user_id, balance)
    return jsonify({"balance": balance})


@app.route("/balances", methods=["GET"])
def balances():
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, balance FROM accounts")
        rows = cur.fetchall()

    return jsonify({r[0]: r[1] for r in rows})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, threaded=True)