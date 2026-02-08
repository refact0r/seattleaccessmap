import pickle
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))
from algorithms.routing import AccessibilityRouter
import networkx as nx
import osmnx as ox

DATA_DIR = Path(__file__).parent / "data_processed"


def log(message):
    print(message.lower())


def load_router():
    with open(DATA_DIR / "graph.pkl", "rb") as f:
        graph = pickle.load(f)
    with open(DATA_DIR / "graph_proj.pkl", "rb") as f:
        graph_proj = pickle.load(f)
    import pandas as pd

    barriers_df = pd.read_pickle(DATA_DIR / "barriers.pkl")
    with open(DATA_DIR / "barrier_tree.pkl", "rb") as f:
        barrier_tree = pickle.load(f)
    with open(DATA_DIR / "config.pkl", "rb") as f:
        config = pickle.load(f)
    return (
        AccessibilityRouter(graph, graph_proj, barriers_df, barrier_tree, config),
        graph_proj,
    )


TEST_ROUTES = [
    (47.6551, -122.3046, 47.6305, -122.3566, "UW -> Queen Anne (example 1)"),
    (47.6552, -122.3045, 47.6205, -122.3212, "UW -> Capitol Hill (example 2)"),
    (47.6155, -122.3210, 47.6095, -122.3270, "Capitol Hill -> First Hill"),
    (47.6090, -122.3370, 47.6015, -122.3340, "Downtown -> Pioneer Square"),
]

SLIDER_VALUES = [0, 10, 25, 40, 50, 60, 75, 90, 99, 100]


def get_edge_data(G_proj, u, v, bw):
    edges = G_proj[u][v]
    if bw >= 0.01:
        best_key = min(
            edges,
            key=lambda k: edges[k].get("length", 0)
            + bw * edges[k].get("accessibility_cost", 0) ** 2,
        )
    else:
        best_key = min(edges, key=lambda k: edges[k].get("length", 0))
    return edges[best_key]


def route_stats(G_proj, route, bw):
    total_length = 0
    total_cost = 0
    for i in range(len(route) - 1):
        data = get_edge_data(G_proj, route[i], route[i + 1], bw)
        total_length += data["length"]
        total_cost += data["accessibility_cost"]
    return total_length, total_cost


def diagnose_edge_costs(G_proj):
    costs = []
    for u, v, data in G_proj.edges(data=True):
        costs.append(data.get("accessibility_cost", 0))

    costs = np.array(costs)
    nonzero = costs > 0
    total = len(costs)
    n_nonzero = nonzero.sum()

    if n_nonzero > 0:
        nz = costs[nonzero]
        return {
            "total": total,
            "nonzero": int(n_nonzero),
            "pct_nonzero": 100 * n_nonzero / total,
            "min": float(nz.min()),
            "p25": float(np.percentile(nz, 25)),
            "median": float(np.median(nz)),
            "p75": float(np.percentile(nz, 75)),
            "max": float(nz.max()),
        }
    return {"total": total, "nonzero": int(n_nonzero), "pct_nonzero": 0.0}


def test_route_divergence(router):
    all_have_gradient = True

    for start_lat, start_lng, end_lat, end_lng, _label in TEST_ROUTES:
        start_node = ox.distance.nearest_nodes(router.G, start_lng, start_lat)
        end_node = ox.distance.nearest_nodes(router.G, end_lng, end_lat)

        prev_route = None
        distinct_routes = 0

        for tolerance in SLIDER_VALUES:
            bw = (100 - tolerance) / 10

            if bw < 0.01:
                route = nx.shortest_path(
                    router.G_proj, start_node, end_node, weight="length"
                )
            else:

                def edge_weight(_u, _v, edge_dict, _bw=bw):
                    return min(
                        d.get("length", 0) + _bw * d.get("accessibility_cost", 0) ** 2
                        for d in edge_dict.values()
                    )

                route = nx.shortest_path(
                    router.G_proj, start_node, end_node, weight=edge_weight
                )

            length, cost = route_stats(router.G_proj, route, bw)

            if prev_route is None or route != prev_route:
                distinct_routes += 1
            prev_route = route

        if distinct_routes <= 2:
            all_have_gradient = False
    return all_have_gradient


def main():
    log("loading router")
    router, G_proj = load_router()
    edge_stats = diagnose_edge_costs(G_proj)
    has_gradient = test_route_divergence(router)

    if has_gradient:
        log("gradient ok")
    else:
        log("gradient warning")

    if edge_stats["total"] == 0:
        log("edge stats: empty")


if __name__ == "__main__":
    main()
