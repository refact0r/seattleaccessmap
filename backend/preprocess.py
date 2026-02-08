from pathlib import Path
import osmnx as ox
import pandas as pd
import pickle
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import LineString
import json
import sys

sys.path.append(str(Path(__file__).parent))
from algorithms.routing import AccessibilityRouter
from algorithms.clustering import generate_clusters

CONFIG = {}

DATA_DIR = Path(__file__).parent / "data_processed"
DATA_DIR.mkdir(exist_ok=True)

FRONTEND_DATA_DIR = Path(__file__).parent.parent / "frontend" / "data"
FRONTEND_DATA_DIR.mkdir(exist_ok=True)


def export_barriers_json(barriers_df):
    """Export barriers in columnar format for compact JSON."""
    label_names = ["CurbRamp", "NoCurbRamp", "NoSidewalk", "Obstacle", "SurfaceProblem", "Other"]
    label_to_idx = {name: i for i, name in enumerate(label_names)}

    temp_indices = barriers_df.index[barriers_df["is_temporary"] == True].tolist()
    # Convert to positional indices
    positions = barriers_df.reset_index(drop=True)
    temp_positional = positions.index[positions["is_temporary"] == True].tolist()

    data = {
        "labels": label_names,
        "lat": [round(v, 5) for v in barriers_df["lat"].tolist()],
        "lng": [round(v, 5) for v in barriers_df["lon"].tolist()],
        "s": barriers_df["severity"].astype(int).tolist(),
        "as": [round(v, 1) for v in barriers_df["adjusted_severity"].tolist()],
        "l": [label_to_idx.get(l, 5) for l in barriers_df["label"].tolist()],
        "t": temp_positional,
    }

    with open(FRONTEND_DATA_DIR / "barriers.json", "w") as f:
        json.dump(data, f, separators=(",", ":"))


def export_clusters_json(clusters_data):
    """Export clusters data, rounding coordinates to 5dp."""

    def round_points(points):
        return [{"lat": round(p["lat"], 5), "lng": round(p["lng"], 5)} for p in points]

    def round_hull(hull):
        if hull is None:
            return None
        return [{"lat": round(p["lat"], 5), "lng": round(p["lng"], 5)} for p in hull]

    clusters = []
    for c in clusters_data["clusters"]:
        cluster = dict(c)
        cluster["points"] = round_points(cluster["points"])
        cluster["hull"] = round_hull(cluster.get("hull"))
        cluster["mean_severity"] = round(cluster["mean_severity"], 2)
        cluster["max_severity"] = round(cluster["max_severity"], 2)
        cluster["spread_m"] = round(cluster["spread_m"], 1)
        cluster["hotspot_score"] = round(cluster["hotspot_score"], 1)
        cluster["lat_center"] = round(cluster["lat_center"], 5)
        cluster["lng_center"] = round(cluster["lng_center"], 5)
        clusters.append(cluster)

    heatmap = [
        [round(lat, 5), round(lng, 5), round(sev, 2)]
        for lat, lng, sev in clusters_data["heatmap_data"]
    ]

    data = {"clusters": clusters, "heatmap_data": heatmap}
    with open(FRONTEND_DATA_DIR / "clusters.json", "w") as f:
        json.dump(data, f, separators=(",", ":"))


def export_analytics_json(barriers_df):
    """Compute analytics (same as app.py /api/analytics) and export as JSON."""
    df = barriers_df

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

    data = {
        "type_counts": type_counts_data,
        "type_severity": type_severity_data,
        "top_neighborhoods": top_neighborhoods,
        "bottom_neighborhoods": bottom_neighborhoods,
        "severity_distribution": severity_distribution,
        "neighborhood_type_severity": neighborhood_type_severity,
    }

    with open(FRONTEND_DATA_DIR / "analytics.json", "w") as f:
        json.dump(data, f, separators=(",", ":"))


def export_fix_priorities_json():
    """Copy fix_priority.geojson to frontend/data/ if it exists."""
    src = Path(__file__).parent / "analysis" / "fix_priority.geojson"
    if src.exists():
        with open(src) as f:
            data = json.load(f)
        with open(FRONTEND_DATA_DIR / "fix_priorities.json", "w") as f:
            json.dump(data, f, separators=(",", ":"))
        return True
    return False


def export_graph_json(G, G_proj):
    """Export graph as JSON with nodes, edges, and edge geometries.

    Uses unprojected graph G for node coordinates (lat/lng) and
    projected graph G_proj for edge costs (length, accessibility_cost).
    """
    # Nodes: { "osmid": [lat, lng], ... }
    nodes = {}
    for node, data in G.nodes(data=True):
        nodes[str(node)] = [round(data["y"], 5), round(data["x"], 5)]

    # Edges: [[u, v, length, acc_cost], ...]
    # For parallel edges between same (u,v), pick the one with minimum length.
    # The graph is a MultiDiGraph with separate (u,v) and (v,u) edges.
    edges = []
    geom = {}

    seen = set()
    for u, v, key, data in G_proj.edges(keys=True, data=True):
        pair = (u, v)
        if pair in seen:
            continue
        seen.add(pair)

        # Among parallel edges (same u,v, different keys), pick lowest length
        all_edges = G_proj[u][v]
        best_key = min(all_edges, key=lambda k: all_edges[k].get("length", 0))
        best = all_edges[best_key]

        length = round(best.get("length", 0), 1)
        acc_cost = round(best.get("accessibility_cost", 0), 1)

        edges.append([u, v, length, acc_cost])

        # Get geometry from unprojected graph G (WGS84 coords)
        if G.has_edge(u, v):
            g_edges = G[u][v]
            g_key = best_key if best_key in g_edges else next(iter(g_edges))
            g_data = g_edges[g_key]
            if "geometry" in g_data:
                line = g_data["geometry"]
                if isinstance(line, LineString):
                    coords = [[round(y, 5), round(x, 5)] for x, y in line.coords]
                    if len(coords) > 2:
                        geom[f"{u},{v}"] = coords

    data = {"nodes": nodes, "edges": edges, "geom": geom}
    with open(FRONTEND_DATA_DIR / "graph.json", "w") as f:
        json.dump(data, f, separators=(",", ":"))


def main():
    def log(message):
        print(message.lower())

    log("loading data")
    barriers_df = pd.read_csv("../data/data_clean.csv")
    barriers_df = barriers_df[barriers_df["adjusted_severity"].notna()].copy()

    log("building clusters")
    clusters_data = generate_clusters(barriers_df, min_severity=4)
    with open(DATA_DIR / "clusters.pkl", "wb") as f:
        pickle.dump(clusters_data, f)

    log("building spatial index")
    mean_lat = barriers_df["lat"].mean()
    cos_lat = np.cos(np.radians(mean_lat))
    CONFIG["cos_lat"] = cos_lat

    barrier_coords = np.column_stack(
        [barriers_df["lat"].values, barriers_df["lon"].values * cos_lat]
    )
    barrier_tree = cKDTree(barrier_coords)

    raw_graph_path = DATA_DIR / "network_raw.pkl"
    raw_graph_proj_path = DATA_DIR / "network_raw_proj.pkl"

    if raw_graph_path.exists() and raw_graph_proj_path.exists():
        log("loading cached network")
        with open(raw_graph_path, "rb") as f:
            G = pickle.load(f)
        with open(raw_graph_proj_path, "rb") as f:
            G_proj = pickle.load(f)
    else:
        log("fetching network")
        G = ox.graph_from_place(
            "Seattle, Washington, USA", network_type="walk", simplify=True
        )
        G_proj = ox.project_graph(G)
        with open(raw_graph_path, "wb") as f:
            pickle.dump(G, f)
        with open(raw_graph_proj_path, "wb") as f:
            pickle.dump(G_proj, f)

    log("calculating edge costs")
    AccessibilityRouter.calculate_edge_costs(
        G, G_proj, barriers_df, barrier_tree, CONFIG
    )

    log("saving pickle outputs")

    with open(DATA_DIR / "graph.pkl", "wb") as f:
        pickle.dump(G, f)

    with open(DATA_DIR / "graph_proj.pkl", "wb") as f:
        pickle.dump(G_proj, f)

    barriers_df.to_pickle(DATA_DIR / "barriers.pkl")

    with open(DATA_DIR / "barrier_tree.pkl", "wb") as f:
        pickle.dump(barrier_tree, f)

    with open(DATA_DIR / "config.pkl", "wb") as f:
        pickle.dump(CONFIG, f)

    log("exporting static json for frontend")

    log("  barriers.json")
    export_barriers_json(barriers_df)

    log("  clusters.json")
    export_clusters_json(clusters_data)

    log("  analytics.json")
    export_analytics_json(barriers_df)

    log("  fix_priorities.json")
    if export_fix_priorities_json():
        log("    copied from analysis/fix_priority.geojson")
    else:
        log("    skipped (fix_priority.geojson not found)")

    log("  graph.json")
    export_graph_json(G, G_proj)

    log(f"done: {DATA_DIR.absolute()}")
    log(f"frontend data: {FRONTEND_DATA_DIR.absolute()}")


if __name__ == "__main__":
    main()
