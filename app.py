from flask import Flask, render_template, request, redirect, session, jsonify
import json

app = Flask(__name__)
app.secret_key = "change_this_secret"
PASSWORD = "admin123"

STATS_FILE = "stats.json"
CONTROL_FILE = "control.json"

def read_stats():
    with open(STATS_FILE, "r") as f:
        return json.load(f)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == PASSWORD:
            session["auth"] = True
            return redirect("/")
    return render_template("login.html")

@app.route("/")
def dashboard():
    if not session.get("auth"):
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/accounts")
def accounts():
    if not session.get("auth"):
        return redirect("/login")
    return render_template("accounts.html", stats=read_stats())

@app.route("/api/stats")
def api_stats():
    return jsonify(read_stats())

@app.route("/control/<action>")
def control(action):
    if not session.get("auth"):
        return redirect("/login")
    with open(CONTROL_FILE, "w") as f:
        json.dump({"run": action == "start"}, f)
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

