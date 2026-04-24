from flask import Flask, request, jsonify

app = Flask(__name__)

registry = {}

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data["name"]
    url = data["url"]

    registry.setdefault(name, [])
    if url not in registry[name]:
        registry[name].append(url)

    print("REGISTER:", name, url)

    return jsonify({"status": "ok"})

@app.route("/services/<name>", methods=["GET"])
def get_service(name):
    return jsonify(registry.get(name, []))

app.run(host="0.0.0.0", port=5003)