from flask import Flask, request, jsonify
import requests
import random
import time
import threading
import hazelcast
import consul
import json
import uuid

app = Flask(__name__)

CONSUL_HOST = "consul"
CONSUL_PORT = 8500


c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


def register():
    service_id = f"facade-{uuid.uuid4()}"

    while True:
        try:
            c.agent.service.register(
                name="facade-service",
                service_id=service_id,
                address="facade-service",
                port=5000,
                check={
                    "http": "http://facade-service:5000/health",
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


def get_services(name):
    try:
        services = c.health.service(name, passing=True)[1]

        return [
            f"http://{s['Service']['Address']}:{s['Service']['Port']}"
            for s in services
        ]
    except Exception as e:
        print("Error getting services:", e)
        return []


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


client = hazelcast.HazelcastClient(
    cluster_name="dev-cluster",
    cluster_members=[
        "hazelcast1:5701",
        "hazelcast2:5701",
        "hazelcast3:5701"
    ]
)

queue = client.get_queue(queue_name).blocking()


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