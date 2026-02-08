import json
import math
import pickle
import random
from collections import Counter
from pathlib import Path

import networkx as nx
import osmnx as ox
import pandas as pd
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent / "data_processed"
CACHE_PATH = Path(__file__).parent / "edge_usage_cache.pkl"


def log(message):
    print(message.lower())


def load_data():
    with open(DATA_DIR / "graph.pkl", "rb") as f:
        G = pickle.load(f)
    with open(DATA_DIR / "graph_proj.pkl", "rb") as f:
        G_proj = pickle.load(f)
    barriers_df = pd.read_pickle(DATA_DIR / "barriers.pkl")
    return G, G_proj, barriers_df


def load_edge_usage_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "rb") as f:
            data = pickle.load(f)
        return data["edge_usage"], data["total_samples"]
    return Counter(), 0


def save_edge_usage_cache(edge_usage, total_samples):
    with open(CACHE_PATH, "wb") as f:
        pickle.dump({"edge_usage": edge_usage, "total_samples": total_samples}, f)


def compute_edge_usage(G_proj, k=500):
    edge_usage, prev_samples = load_edge_usage_cache()

    nodes = list(G_proj.nodes)
    sources = random.sample(nodes, min(k, len(nodes)))

    for source in tqdm(
        sources, desc="sampling shortest paths", unit="node", disable=True
    ):
        try:
            paths = nx.single_source_dijkstra_path(G_proj, source, weight="length")
        except Exception:
            continue
        for path in paths.values():
            for i in range(len(path) - 1):
                edge_usage[(path[i], path[i + 1])] += 1

    total_samples = prev_samples + len(sources)
    save_edge_usage_cache(edge_usage, total_samples)

    return edge_usage


def rank_barriers(G, G_proj, barriers_df, edge_usage):
    nearest = ox.distance.nearest_edges(
        G, barriers_df["lon"].values, barriers_df["lat"].values
    )

    edge_street = {}
    for u, v, key, data in G_proj.edges(keys=True, data=True):
        name = data.get("name", "unnamed")
        if isinstance(name, list):
            name = " / ".join(name)
        edge_street[(u, v, key)] = name

    lats = barriers_df["lat"].values
    lons = barriers_df["lon"].values
    labels = barriers_df["label"].values
    severities = barriers_df["severity"].values
    adj_severities = barriers_df["adjusted_severity"].values
    neighborhoods = (
        barriers_df["neighborhood"].values
        if "neighborhood" in barriers_df.columns
        else [""] * len(barriers_df)
    )

    results = []
    for i in range(len(barriers_df)):
        u, v, key = int(nearest[i][0]), int(nearest[i][1]), int(nearest[i][2])

        usage = edge_usage.get((u, v), 0) + edge_usage.get((v, u), 0)
        if usage == 0:
            continue

        severity = float(adj_severities[i])
        impact = severity * math.log1p(usage)
        street = edge_street.get((u, v, key), "unnamed")

        results.append(
            {
                "lat": float(lats[i]),
                "lng": float(lons[i]),
                "label": str(labels[i]),
                "severity": int(severities[i]),
                "adjusted_severity": severity,
                "usage": usage,
                "impact": impact,
                "street": street,
                "neighborhood": str(neighborhoods[i]),
            }
        )

    results.sort(key=lambda r: r["impact"], reverse=True)
    return results


def export_geojson(results, top_n=200):
    output_dir = Path(__file__).parent
    max_impact = results[0]["impact"] if results else 1

    features = []
    for i, r in enumerate(results[:top_n]):
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["lng"], r["lat"]],
                },
                "properties": {
                    "rank": i + 1,
                    "impact": r["impact"],
                    "impact_normalized": r["impact"] / max_impact,
                    "adjusted_severity": r["adjusted_severity"],
                    "severity": r["severity"],
                    "usage": r["usage"],
                    "label": r["label"],
                    "street": r["street"],
                    "neighborhood": r["neighborhood"],
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    out_path = output_dir / "fix_priority.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f)
    log(f"exported {top_n} barriers to {out_path}")


def main():
    log("loading data")
    G, G_proj, barriers_df = load_data()
    log("computing edge usage")
    edge_usage = compute_edge_usage(G_proj, k=300)
    log("ranking barriers")
    results = rank_barriers(G, G_proj, barriers_df, edge_usage)
    export_geojson(results, top_n=200)


if __name__ == "__main__":
    main()
