from flask import Flask, request, jsonify
import requests
import random
import time
import threading

app = Flask(__name__)

LOGGERS = [
    "http://logging-service1:5001",
    "http://logging-service2:5001",
    "http://logging-service3:5001"
]

COUNTER_URL = "http://counter-service:5002"


def call_logger(payload):
    random.shuffle(LOGGERS)

    for url in LOGGERS:
        try:
            requests.post(f"{url}/log", json=payload, timeout=1)
            return
        except:
            continue


def call_counter(payload):
    r = requests.post(f"{COUNTER_URL}/update", json=payload, timeout=5)
    return r.json()["balance"]


@app.route("/transaction", methods=["POST"])
def transaction():
    data = request.json
    tid = str(time.time())

    payload = {
        "transaction_id": tid,
        "user_id": data["user_id"],
        "amount": data["amount"]
    }

    log_time = 0
    counter_time = 0
    balance = 0

    def log():
        nonlocal log_time
        t = time.time()
        call_logger(payload)
        log_time = time.time() - t

    def counter():
        nonlocal counter_time, balance
        t = time.time()
        balance = call_counter(payload)
        counter_time = time.time() - t

    t1 = threading.Thread(target=log)
    t2 = threading.Thread(target=counter)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    return jsonify({
        "transaction_id": tid,
        "balance": balance,
        "log_time": log_time,
        "counter_time": counter_time
    })


@app.route("/user/<user_id>", methods=["GET"])
def get_user(user_id):
    balances = requests.get(f"{COUNTER_URL}/balances").json()
    balance = balances.get(user_id, 0)

    for url in LOGGERS:
        try:
            logs = requests.get(f"{url}/logs/{user_id}", timeout=1).json()
            return jsonify({
                "balance": balance,
                "transactions": logs
            })
        except:
            continue

    return jsonify({
        "balance": balance,
        "transactions": []
    })


@app.route("/accounts", methods=["GET"])
def get_accounts():
    return jsonify(requests.get(f"{COUNTER_URL}/balances").json())


app.run(host="0.0.0.0", port=5000, threaded=True)