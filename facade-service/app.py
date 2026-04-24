from flask import Flask, request, jsonify
import requests
import time
import threading

app = Flask(__name__)

LOGGING_URL = "http://logging-service:5001"
COUNTER_URL = "http://counter-service:5002"

@app.route("/transaction", methods=["POST"])
def transaction():
    data = request.json
    user_id = data["user_id"]
    amount = data["amount"]

    transaction_id = str(time.time())

    payload = {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "amount": amount
    }

    log_time = 0
    counter_time = 0
    balance = 0

    def call_logging():
        nonlocal log_time
        t = time.time()
        requests.post(f"{LOGGING_URL}/log", json=payload)
        log_time = time.time() - t

    def call_counter():
        nonlocal counter_time, balance
        t = time.time()
        r = requests.post(f"{COUNTER_URL}/update", json=payload)
        counter_time = time.time() - t
        balance = r.json()["balance"]

    t1 = threading.Thread(target=call_logging)
    t2 = threading.Thread(target=call_counter)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    return jsonify({
        "transaction_id": transaction_id,
        "balance": balance,
        "log_time": log_time,
        "counter_time": counter_time
    })

@app.route("/user/<user_id>", methods=["GET"])
def get_user(user_id):
    balance = requests.get(f"{COUNTER_URL}/balance/{user_id}").json()["balance"]
    logs = requests.get(f"{LOGGING_URL}/logs/{user_id}").json()

    return jsonify({
        "balance": balance,
        "transactions": logs
    })

@app.route("/accounts", methods=["GET"])
def get_accounts():
    return jsonify(
        requests.get(f"{COUNTER_URL}/balances").json()
    )

app.run(host="0.0.0.0", port=5000, threaded=True)