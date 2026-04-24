from flask import Flask, request, jsonify

app = Flask(__name__)

balances = {}

from flask import Flask, request, jsonify
from threading import Lock

app = Flask(__name__)

balances = {}
lock = Lock()

@app.route("/update", methods=["POST"])
def update():
    data = request.json
    user_id = data["user_id"]
    amount = data["amount"]

    with lock:
        balances[user_id] = balances.get(user_id, 0) + amount
        balance = balances[user_id]

    return jsonify({"balance": balance})

@app.route("/balance/<user_id>", methods=["GET"])
def get_balance(user_id):
    return jsonify({"balance": balances.get(user_id, 0)})

@app.route("/balances", methods=["GET"])
def all_balances():
    return jsonify(balances)

app.run(host="0.0.0.0", port=5002, threaded=True)