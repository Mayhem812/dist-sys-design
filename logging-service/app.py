from flask import Flask, request, jsonify
import hazelcast
import os
import time
import requests

app = Flask(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "logger")
CONFIG_URL = "http://config-server:5003"


def register():
    while True:
        try:
            requests.post(f"{CONFIG_URL}/register", json={
                "name": "logging-service",
                "url": f"http://{SERVICE_NAME}:5001"
            })
            print("Registered:", SERVICE_NAME)
            break
        except:
            time.sleep(2)

register()


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
        break
    except:
        time.sleep(2)

map = client.get_map("transactions").blocking()

@app.route("/log", methods=["POST"])
def log():
    data = request.json
    map.put(data["transaction_id"], data)

    print(f"[{SERVICE_NAME}] LOGGED:", data)

    return jsonify({"status": "ok"})

@app.route("/logs/<user_id>", methods=["GET"])
def get_logs(user_id):
    all_data = map.values()
    return jsonify([t for t in all_data if t["user_id"] == user_id])

app.run(host="0.0.0.0", port=5001, threaded=True)