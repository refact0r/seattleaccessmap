from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import json

app = Flask(__name__)
CORS(app)

BARRIER_INFLUENCE_RADIUS = 50
SEVERITY_WEIGHT = 1.0
METERS_PER_DEGREE = 111000

G = None
G_proj = None
df_barriers = None
barrier_tree = None


def initialize():
    global G, G_proj, df_barriers, barrier_tree

    print("Loading Seattle pedestrian network...")
    G = ox.graph_from_place(
        "Seattle, Washington, USA", network_type="walk", simplify=True
    )
    G_proj = ox.project_graph(G)
    print(f"Network loaded: {len(G.nodes):,} nodes, {len(G.edges):,} edges")

    print("Loading accessibility barrier data...")
    df_barriers = pd.read_csv("data/data_clean.csv")
    df_barriers = df_barriers[df_barriers["severity"].notna()].copy()
    print(f"Loaded {len(df_barriers):,} barriers with severity ratings")

    print("Building spatial index...")
    barrier_coords = df_barriers[["lat", "lon"]].values
    barrier_tree = cKDTree(barrier_coords)

    print("Calculating edge accessibility costs...")
    calculate_edge_costs()

    print("Server initialization complete!")


def calculate_edge_costs():
    for u, v, key, data in G_proj.edges(keys=True, data=True):
        u_lat = G.nodes[u]["y"]
        u_lng = G.nodes[u]["x"]
        v_lat = G.nodes[v]["y"]
        v_lng = G.nodes[v]["x"]

        mid_lat = (u_lat + v_lat) / 2
        mid_lng = (u_lng + v_lng) / 2

        radius_degrees = BARRIER_INFLUENCE_RADIUS / METERS_PER_DEGREE
        nearby_indices = barrier_tree.query_ball_point(
            [mid_lat, mid_lng], radius_degrees
        )

        if nearby_indices:
            nearby_barriers = df_barriers.iloc[nearby_indices]
            barrier_cost = 0

            for _, barrier in nearby_barriers.iterrows():
                dist = (
                    np.sqrt(
                        (barrier["lat"] - mid_lat) ** 2
                        + (barrier["lon"] - mid_lng) ** 2
                    )
                    * METERS_PER_DEGREE
                )

                if dist < BARRIER_INFLUENCE_RADIUS:
                    proximity_factor = 1 - (dist / BARRIER_INFLUENCE_RADIUS)
                    barrier_cost += barrier["severity"] * proximity_factor

            accessibility_penalty = barrier_cost * SEVERITY_WEIGHT
        else:
            accessibility_penalty = 0

        base_length = data.get("length", 0)
        G_proj[u][v][key]["length"] = base_length
        G_proj[u][v][key]["accessibility_cost"] = accessibility_penalty
        G_proj[u][v][key]["total_cost"] = base_length + accessibility_penalty


@app.route("/calculate_route", methods=["POST"])
def calculate_route():
    try:
        data = request.json
        start_lat = data["start_lat"]
        start_lng = data["start_lng"]
        end_lat = data["end_lat"]
        end_lng = data["end_lng"]

        print(
            f"Calculating route from ({start_lat}, {start_lng}) to ({end_lat}, {end_lng})"
        )

        start_node = ox.distance.nearest_nodes(G, start_lng, start_lat)
        end_node = ox.distance.nearest_nodes(G, end_lng, end_lat)

        route_accessible = nx.shortest_path(
            G_proj, start_node, end_node, weight="total_cost"
        )

        route_standard = nx.shortest_path(G_proj, start_node, end_node, weight="length")

        accessible_length = sum(
            G_proj[route_accessible[i]][route_accessible[i + 1]][0]["length"]
            for i in range(len(route_accessible) - 1)
        )
        accessible_barrier_cost = sum(
            G_proj[route_accessible[i]][route_accessible[i + 1]][0][
                "accessibility_cost"
            ]
            for i in range(len(route_accessible) - 1)
        )

        standard_length = sum(
            G_proj[route_standard[i]][route_standard[i + 1]][0]["length"]
            for i in range(len(route_standard) - 1)
        )
        standard_barrier_cost = sum(
            G_proj[route_standard[i]][route_standard[i + 1]][0]["accessibility_cost"]
            for i in range(len(route_standard) - 1)
        )

        accessible_gdf = ox.routing.route_to_gdf(G, route_accessible)
        standard_gdf = ox.routing.route_to_gdf(G, route_standard)

        accessible_geojson = json.loads(accessible_gdf.to_json())
        standard_geojson = json.loads(standard_gdf.to_json())

        return jsonify(
            {
                "accessible_route": accessible_geojson,
                "standard_route": standard_geojson,
                "stats": {
                    "accessible_length": accessible_length,
                    "accessible_barrier_cost": accessible_barrier_cost,
                    "standard_length": standard_length,
                    "standard_barrier_cost": standard_barrier_cost,
                },
            }
        )

    except nx.NetworkXNoPath:
        return jsonify({"error": "No path found between the specified points"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Routing server is running"})


if __name__ == "__main__":
    print("=" * 60)
    print("ACCESSIBILITY ROUTING SERVER")
    print("=" * 60)
    initialize()
    print("\nStarting Flask server on http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5001, debug=False)
