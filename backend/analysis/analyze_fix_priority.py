"""
Barrier fix prioritization analysis.

Ranks individual barriers by impact: adjusted_severity × log(edge_usage).
High-impact barriers are severe AND sit on heavily-trafficked paths with few alternatives.

Usage: python3 backend/analysis/analyze_fix_priority.py
"""

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


def load_data():
    print("Loading preprocessed data...")
    with open(DATA_DIR / "graph.pkl", "rb") as f:
        G = pickle.load(f)
    with open(DATA_DIR / "graph_proj.pkl", "rb") as f:
        G_proj = pickle.load(f)
    barriers_df = pd.read_pickle(DATA_DIR / "barriers.pkl")
    print(f"  {len(G_proj.nodes):,} nodes, {len(G_proj.edges):,} edges")
    print(f"  {len(barriers_df):,} barriers")
    return G, G_proj, barriers_df


def load_edge_usage_cache():
    """Load cached edge usage counts from previous runs."""
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "rb") as f:
            data = pickle.load(f)
        print(f"  Loaded cached edge usage ({data['total_samples']:,} previous samples)")
        return data["edge_usage"], data["total_samples"]
    return Counter(), 0


def save_edge_usage_cache(edge_usage, total_samples):
    """Save edge usage counts for future runs."""
    with open(CACHE_PATH, "wb") as f:
        pickle.dump({"edge_usage": edge_usage, "total_samples": total_samples}, f)
    print(f"  Saved edge usage cache ({total_samples:,} total samples, {CACHE_PATH.stat().st_size / 1024:.0f} KB)")


def compute_edge_usage(G_proj, k=500):
    """Approximate edge betweenness via sampled shortest paths.

    Resumes from cached results if available, adding k new samples each run.
    """
    edge_usage, prev_samples = load_edge_usage_cache()

    nodes = list(G_proj.nodes)
    sources = random.sample(nodes, min(k, len(nodes)))

    for source in tqdm(sources, desc="Sampling shortest paths", unit="node"):
        try:
            paths = nx.single_source_dijkstra_path(G_proj, source, weight="length")
        except Exception:
            continue
        for path in paths.values():
            for i in range(len(path) - 1):
                edge_usage[(path[i], path[i + 1])] += 1

    total_samples = prev_samples + len(sources)
    save_edge_usage_cache(edge_usage, total_samples)
    print(f"  Total: {total_samples:,} samples ({prev_samples:,} cached + {len(sources):,} new)")

    return edge_usage


def rank_barriers(G, G_proj, barriers_df, edge_usage):
    """Snap barriers to edges and rank by adjusted_severity × log(edge_usage)."""
    print("Snapping barriers to nearest edges...")
    nearest = ox.distance.nearest_edges(
        G, barriers_df["lon"].values, barriers_df["lat"].values
    )

    # Build edge street name lookup from projected graph
    edge_street = {}
    for u, v, key, data in G_proj.edges(keys=True, data=True):
        name = data.get("name", "unnamed")
        if isinstance(name, list):
            name = " / ".join(name)
        edge_street[(u, v, key)] = name

    # Extract arrays for fast iteration (avoids pandas iloc overhead)
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

        # Sum usage in both directions (graph is effectively undirected for walking)
        usage = edge_usage.get((u, v), 0) + edge_usage.get((v, u), 0)
        if usage == 0:
            continue

        severity = float(adj_severities[i])
        impact = severity * math.log1p(usage)
        street = edge_street.get((u, v, key), "unnamed")

        results.append({
            "lat": float(lats[i]),
            "lng": float(lons[i]),
            "label": str(labels[i]),
            "severity": int(severities[i]),
            "adjusted_severity": severity,
            "usage": usage,
            "impact": impact,
            "street": street,
            "neighborhood": str(neighborhoods[i]),
        })

    results.sort(key=lambda r: r["impact"], reverse=True)
    print(f"  Scored {len(results):,} barriers on trafficked edges")
    return results


def print_results(results, top_n=30):
    total = len(results)
    total_impact = sum(r["impact"] for r in results)

    print(f"\n{'=' * 130}")
    print(f"BARRIER FIX PRIORITIZATION — TOP {top_n} INDIVIDUAL BARRIERS")
    print(f"{'=' * 130}")
    print(f"  {total:,} barriers scored")
    print(f"  Metric: impact = adjusted_severity x edge_usage")
    print(f"  High impact = severe barrier on a heavily-used path\n")

    cumulative = 0
    print(f"{'Rank':<5} {'Impact':>8} {'Cum%':>6} {'Sev':>5} {'Usage':>7} "
          f"{'Label':<16} {'Street':<28} {'Location':<24} {'Neighborhood'}")
    print("-" * 130)

    for i, r in enumerate(results[:top_n]):
        cumulative += r["impact"]
        cum_pct = 100 * cumulative / total_impact if total_impact else 0
        print(
            f"{i+1:<5} {r['impact']:>8,.0f} {cum_pct:>5.1f}% {r['adjusted_severity']:>5.1f} "
            f"{r['usage']:>7,} {r['label']:<16} {r['street']:<28} "
            f"({r['lat']:.4f}, {r['lng']:.4f})  {r['neighborhood']}"
        )

    # Label type breakdown in top N
    print(f"\n{'=' * 130}")
    print(f"BARRIER TYPE BREAKDOWN — TOP {top_n}")
    print(f"{'=' * 130}\n")

    type_counts = Counter(r["label"] for r in results[:top_n])
    type_impact = {}
    for r in results[:top_n]:
        type_impact[r["label"]] = type_impact.get(r["label"], 0) + r["impact"]

    print(f"{'Label':<16} {'Count':>6} {'Total Impact':>13} {'Avg Impact':>11}")
    print("-" * 50)
    for label, count in type_counts.most_common():
        avg = type_impact[label] / count
        print(f"{label:<16} {count:>6} {type_impact[label]:>13,.0f} {avg:>11,.0f}")

    # Top streets aggregated
    print(f"\n{'=' * 130}")
    print("TOP STREETS BY TOTAL BARRIER IMPACT")
    print(f"{'=' * 130}\n")

    street_agg = {}
    for r in results:
        name = r["street"]
        if name == "unnamed":
            continue
        if name not in street_agg:
            street_agg[name] = {"impact": 0, "count": 0, "worst_lat": 0, "worst_lng": 0, "worst_impact": 0}
        street_agg[name]["impact"] += r["impact"]
        street_agg[name]["count"] += 1
        if r["impact"] > street_agg[name]["worst_impact"]:
            street_agg[name]["worst_impact"] = r["impact"]
            street_agg[name]["worst_lat"] = r["lat"]
            street_agg[name]["worst_lng"] = r["lng"]

    street_ranked = sorted(street_agg.items(), key=lambda x: x[1]["impact"], reverse=True)

    print(f"{'Rank':<5} {'Impact':>9} {'#Barriers':>10}  {'Street':<30} {'Worst barrier location'}")
    print("-" * 85)
    for i, (name, s) in enumerate(street_ranked[:20]):
        print(f"{i+1:<5} {s['impact']:>9,.0f} {s['count']:>10}  {name:<30} ({s['worst_lat']:.4f}, {s['worst_lng']:.4f})")


def export_geojson(results, top_n=200):
    """Export top barriers as GeoJSON Points with impact properties."""
    output_dir = Path(__file__).parent
    max_impact = results[0]["impact"] if results else 1

    features = []
    for i, r in enumerate(results[:top_n]):
        features.append({
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
        })

    geojson = {"type": "FeatureCollection", "features": features}
    out_path = output_dir / "fix_priority.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f)
    print(f"\nExported top {top_n} barriers to {out_path}")


def main():
    G, G_proj, barriers_df = load_data()
    edge_usage = compute_edge_usage(G_proj, k=300)
    results = rank_barriers(G, G_proj, barriers_df, edge_usage)
    print_results(results, top_n=30)
    export_geojson(results, top_n=200)


if __name__ == "__main__":
    main()
