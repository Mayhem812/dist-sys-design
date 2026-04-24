from flask import Flask, request, jsonify
import hazelcast
import os
import time

app = Flask(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "logger")

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

map = client.get_map("transactions").blocking()


@app.route("/log", methods=["POST"])
def log():
    data = request.json
    tid = data["transaction_id"]

    map.put(tid, data)

    print(f"[{SERVICE_NAME}] LOGGED:", data)

    return jsonify({"status": "ok"})


@app.route("/logs/<user_id>", methods=["GET"])
def get_logs(user_id):
    all_data = map.values()

    return jsonify([
        t for t in all_data if t["user_id"] == user_id
    ])


app.run(host="0.0.0.0", port=5001, threaded=True)