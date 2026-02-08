"""
Barrier fix prioritization analysis.

Ranks barriers by impact: accessibility_cost × edge_betweenness_centrality.
High-impact barriers are severe AND sit on heavily-trafficked paths with few alternatives.

Usage: python3 backend/analysis/analyze_fix_priority.py
"""

import json
import pickle
import random
from collections import Counter
from pathlib import Path
import networkx as nx
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent / "data_processed"


def load_data():
    print("Loading preprocessed graph data...")
    with open(DATA_DIR / "graph.pkl", "rb") as f:
        G = pickle.load(f)
    with open(DATA_DIR / "graph_proj.pkl", "rb") as f:
        G_proj = pickle.load(f)
    print(f"  {len(G_proj.nodes):,} nodes, {len(G_proj.edges):,} edges")
    return G, G_proj


def compute_edge_usage(G_proj, k=500):
    """Approximate edge betweenness via sampled shortest paths with progress bar.

    For each of k random source nodes, computes shortest paths to all reachable
    nodes and counts how many times each edge (u, v) is traversed.
    """
    nodes = list(G_proj.nodes)
    sources = random.sample(nodes, min(k, len(nodes)))

    edge_usage = Counter()

    for source in tqdm(sources, desc="Sampling shortest paths", unit="node"):
        try:
            paths = nx.single_source_dijkstra_path(G_proj, source, weight="length")
        except Exception:
            continue
        for path in paths.values():
            for i in range(len(path) - 1):
                edge_usage[(path[i], path[i + 1])] += 1

    return edge_usage


def rank_edges(G, G_proj, edge_usage):
    """Combine barrier cost with edge usage to rank edges by fix priority."""
    results = []

    for (u, v), usage in edge_usage.items():
        if not G_proj.has_edge(u, v):
            continue

        # Pick the parallel edge with highest barrier cost (the one that matters)
        edges = G_proj[u][v]
        best_key = max(edges, key=lambda k: edges[k].get("accessibility_cost", 0))
        data = edges[best_key]

        cost = data.get("accessibility_cost", 0)
        if cost == 0:
            continue

        barrier_count = data.get("barrier_count", 0)
        length = data.get("length", 0)
        street = data.get("name", "unnamed")
        if isinstance(street, list):
            street = " / ".join(street)

        impact = cost * usage

        # Get lat/lng from unprojected graph (midpoint of edge)
        if G.has_node(u) and G.has_node(v):
            lat = (G.nodes[u]["y"] + G.nodes[v]["y"]) / 2
            lng = (G.nodes[u]["x"] + G.nodes[v]["x"]) / 2
        else:
            lat, lng = 0, 0

        results.append({
            "u": u,
            "v": v,
            "key": best_key,
            "street": street,
            "lat": lat,
            "lng": lng,
            "barrier_count": barrier_count,
            "accessibility_cost": cost,
            "usage": usage,
            "impact": impact,
            "length_m": length,
        })

    results.sort(key=lambda r: r["impact"], reverse=True)
    return results


def print_results(results, top_n=30):
    # Summary stats
    total_barrier_edges = len(results)
    total_barriers = sum(r["barrier_count"] for r in results)
    total_impact = sum(r["impact"] for r in results)

    print(f"\n{'=' * 80}")
    print(f"BARRIER FIX PRIORITIZATION — TOP {top_n} EDGES")
    print(f"{'=' * 80}")
    print(f"  {total_barrier_edges:,} edges have barriers ({total_barriers:,} total barrier points)")
    print(f"  Metric: impact = accessibility_cost × betweenness_centrality")
    print(f"  High impact = severe barrier on a heavily-used path with few alternatives\n")

    # Cumulative impact
    cumulative = 0
    print(f"{'Rank':<5} {'Impact':>9} {'Cum%':>6} {'Cost':>6} {'Usage':>7} "
          f"{'#Bar':>5} {'Len(m)':>7}  {'Street':<30} {'Location'}")
    print("-" * 120)

    for i, r in enumerate(results[:top_n]):
        cumulative += r["impact"]
        cum_pct = 100 * cumulative / total_impact
        print(
            f"{i+1:<5} {r['impact']:>9,} {cum_pct:>5.1f}% {r['accessibility_cost']:>6.1f} "
            f"{r['usage']:>7,} {r['barrier_count']:>5} {r['length_m']:>7.1f}  "
            f"{r['street']:<30} ({r['lat']:.4f}, {r['lng']:.4f})"
        )

    # Show how much fixing the top N addresses
    top_impact = sum(r["impact"] for r in results[:top_n])
    print(f"\n{'=' * 80}")
    print(f"Fixing the top {top_n} edges addresses {100 * top_impact / total_impact:.1f}% of total network impact.")
    print(f"These edges contain {sum(r['barrier_count'] for r in results[:top_n]):,} "
          f"of {total_barriers:,} total barrier points ({100 * sum(r['barrier_count'] for r in results[:top_n]) / total_barriers:.1f}%).")

    # Top streets aggregated
    print(f"\n{'=' * 80}")
    print("TOP STREETS (aggregated across all edges)")
    print(f"{'=' * 80}\n")

    street_impact = {}
    for r in results:
        name = r["street"]
        if name not in street_impact:
            street_impact[name] = {"impact": 0, "cost": 0, "barriers": 0, "edges": 0, "worst_lat": 0, "worst_lng": 0, "worst_impact": 0}
        street_impact[name]["impact"] += r["impact"]
        street_impact[name]["cost"] += r["accessibility_cost"]
        street_impact[name]["barriers"] += r["barrier_count"]
        street_impact[name]["edges"] += 1
        # Track location of the worst edge on this street
        if r["impact"] > street_impact[name]["worst_impact"]:
            street_impact[name]["worst_impact"] = r["impact"]
            street_impact[name]["worst_lat"] = r["lat"]
            street_impact[name]["worst_lng"] = r["lng"]

    # Remove unnamed, sort by impact
    street_ranked = sorted(
        ((k, v) for k, v in street_impact.items() if k != "unnamed"),
        key=lambda x: x[1]["impact"],
        reverse=True,
    )

    print(f"{'Rank':<5} {'Impact':>8} {'Cost':>7} {'#Bar':>5} {'#Edges':>6}  {'Street':<30} {'Worst edge location'}")
    print("-" * 95)
    for i, (name, s) in enumerate(street_ranked[:20]):
        print(f"{i+1:<5} {s['impact']:>8.5f} {s['cost']:>7.1f} {s['barriers']:>5} {s['edges']:>6}  {name:<30} ({s['worst_lat']:.4f}, {s['worst_lng']:.4f})")


def export_geojson(results, G, top_n=50):
    """Export top edges as GeoJSON LineStrings with impact properties."""
    output_dir = Path(__file__).parent
    max_impact = results[0]["impact"] if results else 1

    features = []
    for i, r in enumerate(results[:top_n]):
        u, v, key = r["u"], r["v"], r["key"]

        # Use actual edge geometry from OSMnx if available, otherwise straight line
        edge_data = G[u][v][key] if G.has_edge(u, v, key) else {}
        if "geometry" in edge_data:
            coords = list(edge_data["geometry"].coords)
        else:
            coords = [
                [G.nodes[u]["x"], G.nodes[u]["y"]],
                [G.nodes[v]["x"], G.nodes[v]["y"]],
            ]

        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "rank": i + 1,
                "impact": r["impact"],
                "impact_normalized": r["impact"] / max_impact,
                "accessibility_cost": r["accessibility_cost"],
                "usage": r["usage"],
                "barrier_count": r["barrier_count"],
                "length_m": round(r["length_m"], 1),
                "street": r["street"],
            },
        })

    geojson = {"type": "FeatureCollection", "features": features}
    out_path = output_dir / "fix_priority.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f)
    print(f"\nExported top {top_n} edges to {out_path}")


def main():
    G, G_proj = load_data()
    edge_usage = compute_edge_usage(G_proj, k=30)
    results = rank_edges(G, G_proj, edge_usage)
    print_results(results, top_n=30)
    export_geojson(results, G, top_n=50)


if __name__ == "__main__":
    main()
