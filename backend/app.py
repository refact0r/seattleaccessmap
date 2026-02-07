"""
Flask API server - Loads preprocessed data once at startup.
Provides endpoints for routing and analysis.
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import pickle
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Load preprocessed data once at startup
data_path = Path(__file__).parent / "data_processed" / "data.pkl"
if data_path.exists():
    with open(data_path, "rb") as f:
        DATA = pickle.load(f)
    print(f"Loaded {len(DATA)} records into memory")
else:
    DATA = None
    print("Warning: No preprocessed data found. Run preprocess.py first.")

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "records": len(DATA) if DATA is not None else 0})

@app.route("/api/route", methods=["POST"])
def route():
    # TODO: Implement routing algorithm
    params = request.json
    return jsonify({"message": "Route endpoint - not implemented yet", "params": params})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
