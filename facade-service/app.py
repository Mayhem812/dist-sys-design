from flask import Flask, request, jsonify
import requests
import random
import time
import threading
import hazelcast

app = Flask(__name__)

CONFIG_URL = "http://config-server:5003"


def register():
    while True:
        try:
            requests.post(f"{CONFIG_URL}/register", json={
                "name": "facade-service",
                "url": "http://facade-service:5000"
            })
            print("Registered in config-server")
            break
        except:
            time.sleep(2)

register()


def get_services(name):
    return requests.get(f"{CONFIG_URL}/services/{name}").json()


client = hazelcast.HazelcastClient(
    cluster_name="dev-cluster",
    cluster_members=[
        "hazelcast1:5701",
        "hazelcast2:5701",
        "hazelcast3:5701"
    ]
)

queue = client.get_queue("transactions-queue").blocking()


def call_logger(payload):
    loggers = get_services("logging-service")
    random.shuffle(loggers)

    for url in loggers:
        try:
            requests.post(f"{url}/log", json=payload, timeout=1)
            return
        except:
            continue


@app.route("/transaction", methods=["POST"])
def transaction():
    data = request.json
    tid = str(time.time())

    payload = {
        "transaction_id": tid,
        "user_id": data["user_id"],
        "amount": data["amount"]
    }

    threading.Thread(target=call_logger, args=(payload,)).start()

    queue.put(payload)

    return jsonify({
        "transaction_id": tid,
        "status": "queued"
    })


@app.route("/user/<user_id>", methods=["GET"])
def get_user(user_id):
    counters = get_services("counter-service")

    balance = 0
    if counters:
        try:
            balances = requests.get(f"{counters[0]}/balances").json()
            balance = balances.get(user_id, 0)
        except:
            balance = None

    loggers = get_services("logging-service")

    for url in loggers:
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
    counters = get_services("counter-service")

    if not counters:
        return jsonify({})

    try:
        return jsonify(requests.get(f"{counters[0]}/balances").json())
    except:
        return jsonify({})


app.run(host="0.0.0.0", port=5000, threaded=True)