from flask import Flask

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return "", 200  # empty body, status 200

if __name__ == "__main__":
    # Must listen on 0.0.0.0:8080 for the Council infrastructure
    app.run(host="0.0.0.0", port=8080)
