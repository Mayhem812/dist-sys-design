from flask import Flask, request, jsonify
from threading import Lock

app = Flask(__name__)

transactions = {}
lock = Lock()

@app.route("/log", methods=["POST"])
def log():
    data = request.json
    transaction_id = data["transaction_id"]

    with lock:
        transactions[transaction_id] = data

    return jsonify({"status": "ok"})

@app.route("/logs/<user_id>", methods=["GET"])
def get_logs(user_id):
    return jsonify([
        t for t in transactions.values() if t["user_id"] == user_id
    ])

@app.route("/logs", methods=["GET"])
def all_logs():
    return jsonify(list(transactions.values()))

app.run(host="0.0.0.0", port=5001, threaded=True)