from flask import Flask, request, jsonify
import hazelcast
import os
import time
import requests
import consul
import json
import uuid

app = Flask(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "logger")

CONSUL_HOST = "consul"
CONSUL_PORT = 8500


c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


def register():
    service_id = f"{SERVICE_NAME}-{uuid.uuid4()}"

    while True:
        try:
            c.agent.service.register(
                name="logging-service",
                service_id=service_id,
                address=SERVICE_NAME,
                port=5001,
                check={
                    "http": f"http://{SERVICE_NAME}:5001/health",
                    "interval": "5s",
                    "timeout": "2s"
                }
            )
            print(f"Registered in Consul: {SERVICE_NAME}")
            break
        except Exception as e:
            print("Consul not ready, retrying...", e)
            time.sleep(2)

register()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": SERVICE_NAME})


def load_hazelcast_config():
    while True:
        try:
            _, data = c.kv.get("hazelcast/config")

            if data is None:
                raise Exception("Hazelcast config not found yet")

            config = json.loads(data["Value"])
            print("Hazelcast config loaded:", config)
            return config

        except Exception as e:
            print("Waiting for hazelcast config...", e)
            time.sleep(2)

hz_config = load_hazelcast_config()
cluster_members = hz_config["members"]


client = None
for i in range(10):
    try:
        client = hazelcast.HazelcastClient(
            cluster_name="dev-cluster",
            cluster_members=cluster_members
        )
        print("Connected to Hazelcast")
        break
    except Exception as e:
        print("Waiting for Hazelcast...", e)
        time.sleep(2)

if client is None:
    raise Exception("Hazelcast connection failed")

map = client.get_map("transactions").blocking()


total_log_time = 0.0


@app.route("/log", methods=["POST"])
def log():
    global total_log_time

    data = request.json

    t = time.time()
    map.put(data["transaction_id"], data)
    total_log_time += (time.time() - t)

    return jsonify({"status": "ok"})


@app.route("/logs/<user_id>", methods=["GET"])
def get_logs(user_id):
    all_data = map.values()
    return jsonify([t for t in all_data if t["user_id"] == user_id])


@app.route("/metrics", methods=["GET"])
def metrics():
    return jsonify({
        "total_log_time": total_log_time
    })

app.run(host="0.0.0.0", port=5001, threaded=True)