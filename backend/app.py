from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from algorithms.routing import AccessibilityRouter

app = Flask(__name__)
CORS(app)

router = None
clusters_data = None
barriers_cache = None
fix_priorities_data = None
barriers_df_global = None


def load_preprocessed_data():
    global router, clusters_data, barriers_cache, fix_priorities_data, barriers_df_global

    data_dir = Path(__file__).parent / "data_processed"

    print("Loading preprocessed data...")

    try:
        with open(data_dir / "graph.pkl", "rb") as f:
            graph = pickle.load(f)

        with open(data_dir / "graph_proj.pkl", "rb") as f:
            graph_proj = pickle.load(f)

        barriers_df = pd.read_pickle(data_dir / "barriers.pkl")
        barriers_df_global = barriers_df

        with open(data_dir / "barrier_tree.pkl", "rb") as f:
            barrier_tree = pickle.load(f)

        with open(data_dir / "config.pkl", "rb") as f:
            config = pickle.load(f)

        with open(data_dir / "clusters.pkl", "rb") as f:
            clusters_data = pickle.load(f)

        router = AccessibilityRouter(
            graph, graph_proj, barriers_df, barrier_tree, config
        )

        print(
            f"✓ Loaded network: {len(graph.nodes):,} nodes, {len(graph.edges):,} edges"
        )
        print(f"✓ Loaded {len(barriers_df):,} barriers")
        print(f"✓ Loaded {len(clusters_data['clusters'])} clusters")

        cache_cols = [
            "lat",
            "lon",
            "severity",
            "adjusted_severity",
            "label",
            "is_temporary",
        ]
        df = barriers_df[[c for c in cache_cols if c in barriers_df.columns]].copy()
        df = df.rename(columns={"lon": "lng"})
        df["adjusted_severity"] = df["adjusted_severity"].round(1)
        df["severity"] = df["severity"].astype(int)
        barriers_cache = df.to_dict("records")
        print(f"✓ Cached {len(barriers_cache):,} barriers for API")

        fix_priority_path = Path(__file__).parent / "analysis" / "fix_priority.geojson"
        if fix_priority_path.exists():
            with open(fix_priority_path) as f:
                fix_priorities_data = json.load(f)
            print(
                f"✓ Loaded {len(fix_priorities_data['features'])} fix priority barriers"
            )
        else:
            print(
                "⚠ fix_priority.geojson not found (run analyze_fix_priority.py to generate)"
            )

        print("✓ Router initialized and ready!")

    except FileNotFoundError as e:
        print(f"\n❌ Error: Preprocessed data not found!")
        print(f"   Missing file: {e.filename}")
        print("\n   Please run preprocessing first:")
        print("   python3 backend/preprocess.py\n")
        sys.exit(1)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "message": "Accessibility routing server is running",
            "router_ready": router is not None,
        }
    )


@app.route("/api/barriers", methods=["GET"])
def get_barriers():
    if barriers_cache is None:
        return jsonify({"error": "Barrier data not loaded"}), 500

    return jsonify(barriers_cache)


@app.route("/api/clusters", methods=["GET"])
def get_clusters():
    if clusters_data is None:
        return jsonify({"error": "Cluster data not loaded"}), 500

    return jsonify(clusters_data)


@app.route("/api/fix_priorities", methods=["GET"])
def get_fix_priorities():
    if fix_priorities_data is None:
        return (
            jsonify(
                {
                    "error": "Fix priority data not generated. Run analyze_fix_priority.py first."
                }
            ),
            500,
        )

    return jsonify(fix_priorities_data)


@app.route("/api/calculate_route", methods=["POST"])
def calculate_route():
    if router is None:
        return jsonify({"error": "Router not initialized"}), 500

    try:
        data = request.json
        start_lat = data["start_lat"]
        start_lng = data["start_lng"]
        end_lat = data["end_lat"]
        end_lng = data["end_lng"]
        barrier_weight = data.get("barrier_weight", 1.0)

        print(f"Calculating route: ({start_lat}, {start_lng}) → ({end_lat}, {end_lng})")
        print(f"  Barrier weight: {barrier_weight:.2f}")

        result = router.calculate_route(
            start_lat, start_lng, end_lat, end_lng, barrier_weight
        )

        print(f"✓ Routes calculated successfully")

        return jsonify(result)

    except ValueError as e:
        print(f"ValueError: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        print(f"KeyError: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Missing parameter: {e}"}), 400
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    if barriers_df_global is None:
        return jsonify({"error": "Data not loaded"}), 500

    df = barriers_df_global

    type_counts = df["label"].value_counts()
    type_counts_data = {
        "labels": type_counts.index.tolist(),
        "values": type_counts.values.tolist(),
    }

    type_sev = df.groupby("label")["severity"].mean().sort_values(ascending=False)
    type_severity_data = {
        "labels": type_sev.index.tolist(),
        "values": [round(v, 2) for v in type_sev.values.tolist()],
    }

    neigh_counts = df["neighborhood"].value_counts()
    top_n = neigh_counts.head(10)
    top_neighborhoods = {
        "labels": top_n.index.tolist(),
        "values": top_n.values.tolist(),
    }

    bottom_n = neigh_counts.tail(10).sort_values(ascending=True)
    bottom_neighborhoods = {
        "labels": bottom_n.index.tolist(),
        "values": bottom_n.values.tolist(),
    }

    bins = np.arange(0, 11, 0.5)
    hist_values, hist_edges = np.histogram(df["adjusted_severity"], bins=bins)
    severity_distribution = {
        "labels": [f"{e:.1f}" for e in hist_edges[:-1]],
        "values": hist_values.tolist(),
    }

    types = sorted(df["label"].unique().tolist())
    neighborhoods = sorted(df["neighborhood"].unique().tolist())
    pivot = df.pivot_table(
        values="adjusted_severity",
        index="neighborhood",
        columns="label",
        aggfunc="mean",
    ).reindex(index=neighborhoods, columns=types)

    matrix = []
    for n in neighborhoods:
        row = []
        for t in types:
            val = pivot.loc[n, t]
            row.append(round(float(val), 2) if pd.notna(val) else None)
        matrix.append(row)

    neighborhood_type_severity = {
        "neighborhoods": neighborhoods,
        "types": types,
        "matrix": matrix,
    }

    return jsonify(
        {
            "type_counts": type_counts_data,
            "type_severity": type_severity_data,
            "top_neighborhoods": top_neighborhoods,
            "bottom_neighborhoods": bottom_neighborhoods,
            "severity_distribution": severity_distribution,
            "neighborhood_type_severity": neighborhood_type_severity,
        }
    )


if __name__ == "__main__":
    print("=" * 60)
    print("ACCESSIBILITY ROUTING API SERVER")
    print("=" * 60)

    load_preprocessed_data()

    print("\n" + "=" * 60)
    print("Starting Flask server on http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", port=5001, debug=False)
