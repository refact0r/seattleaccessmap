"""
Test whether barrier_weight (tolerance) produces a gradient of routes.

Verifies:
1. Edge cost distribution (what % of edges have barriers)
2. Different slider values produce different node sequences (not binary)
3. Stats are computed using correct multigraph edge selection
"""

import pickle
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))
from algorithms.routing import AccessibilityRouter
import networkx as nx
import osmnx as ox

DATA_DIR = Path(__file__).parent / 'data_processed'


def load_router():
    with open(DATA_DIR / 'graph.pkl', 'rb') as f:
        graph = pickle.load(f)
    with open(DATA_DIR / 'graph_proj.pkl', 'rb') as f:
        graph_proj = pickle.load(f)
    import pandas as pd
    barriers_df = pd.read_pickle(DATA_DIR / 'barriers.pkl')
    with open(DATA_DIR / 'barrier_tree.pkl', 'rb') as f:
        barrier_tree = pickle.load(f)
    with open(DATA_DIR / 'config.pkl', 'rb') as f:
        config = pickle.load(f)
    return AccessibilityRouter(graph, graph_proj, barriers_df, barrier_tree, config), graph_proj


TEST_ROUTES = [
    (47.6062, -122.3321, 47.6205, -122.3493, "Pioneer Sq -> Pike Place (example 1)"),
    (47.6553, -122.3035, 47.6205, -122.3212, "UW -> Capitol Hill (example 2)"),
    (47.6155, -122.3210, 47.6095, -122.3270, "Capitol Hill -> First Hill"),
    (47.6090, -122.3370, 47.6015, -122.3340, "Downtown -> Pioneer Square"),
]

# Frontend slider: tolerance 0-100 -> bw = (100 - t) / 10
SLIDER_VALUES = [0, 10, 25, 40, 50, 60, 75, 90, 99, 100]


def get_edge_data(G_proj, u, v, bw):
    """Pick the edge Dijkstra would use between u and v (min weight among parallel edges)."""
    edges = G_proj[u][v]
    if bw >= 0.01:
        best_key = min(edges, key=lambda k: edges[k].get('length', 0) + bw * edges[k].get('accessibility_cost', 0) ** 2)
    else:
        best_key = min(edges, key=lambda k: edges[k].get('length', 0))
    return edges[best_key]


def route_stats(G_proj, route, bw):
    """Compute stats using correct multigraph edge selection."""
    total_length = 0
    total_cost = 0
    for i in range(len(route) - 1):
        data = get_edge_data(G_proj, route[i], route[i + 1], bw)
        total_length += data['length']
        total_cost += data['accessibility_cost']
    return total_length, total_cost


def diagnose_edge_costs(G_proj):
    """Check edge cost distribution."""
    print("=" * 70)
    print("DIAGNOSIS: Edge accessibility_cost distribution")
    print("=" * 70)

    costs = []
    lengths = []
    for u, v, data in G_proj.edges(data=True):
        costs.append(data.get('accessibility_cost', 0))
        lengths.append(data.get('length', 0))

    costs = np.array(costs)
    lengths = np.array(lengths)
    nonzero = costs > 0
    total = len(costs)
    n_nonzero = nonzero.sum()

    print(f"\n  Total edges:           {total:,}")
    print(f"  Edges with cost > 0:   {n_nonzero:,} ({100*n_nonzero/total:.2f}%)")

    if n_nonzero > 0:
        nz = costs[nonzero]
        print(f"\n  Cost distribution (non-zero edges):")
        print(f"    min={nz.min():.2f}  p25={np.percentile(nz,25):.2f}  "
              f"median={np.median(nz):.2f}  p75={np.percentile(nz,75):.2f}  max={nz.max():.2f}")
        print(f"\n  With cost^2 penalty:")
        print(f"    median cost^2 = {np.median(nz)**2:.1f}")
        print(f"    max cost^2    = {nz.max()**2:.1f}")
    print()


def test_route_divergence(router):
    """Test whether the frontend slider range produces a gradient of routes."""
    print("=" * 70)
    print("TEST: Do routes form a gradient across the slider range?")
    print("  (formula: weight = length + bw * cost^2)")
    print("=" * 70)

    all_have_gradient = True

    for start_lat, start_lng, end_lat, end_lng, label in TEST_ROUTES:
        print(f"\n  ROUTE: {label}")

        start_node = ox.distance.nearest_nodes(router.G, start_lng, start_lat)
        end_node = ox.distance.nearest_nodes(router.G, end_lng, end_lat)

        print(f"\n    {'slider':>6} {'bw':>6} | {'nodes':>6} | {'dist (m)':>9} | {'barrier':>10} | route vs shortest")
        print(f"    {'-'*6} {'-'*6}-+-{'-'*6}-+-{'-'*9}-+-{'-'*10}-+------------------")

        routes = {}
        prev_route = None
        distinct_routes = 0

        for tolerance in SLIDER_VALUES:
            bw = (100 - tolerance) / 10

            if bw < 0.01:
                route = nx.shortest_path(router.G_proj, start_node, end_node, weight='length')
            else:
                def edge_weight(_u, _v, edge_dict, _bw=bw):
                    return min(
                        d.get('length', 0) + _bw * d.get('accessibility_cost', 0) ** 2
                        for d in edge_dict.values()
                    )
                route = nx.shortest_path(router.G_proj, start_node, end_node, weight=edge_weight)

            length, cost = route_stats(router.G_proj, route, bw)

            # Compare to previous slider value
            if prev_route is None or route != prev_route:
                distinct_routes += 1
            changed = "  << NEW" if (prev_route is not None and route != prev_route) else ""

            # Compare to shortest (bw=0)
            shortest = routes.get(100, {}).get('route')
            if shortest and route != shortest:
                std_edges = set(zip(shortest[:-1], shortest[1:]))
                acc_edges = set(zip(route[:-1], route[1:]))
                diff = len(std_edges.symmetric_difference(acc_edges))
                tag = f"DIFFERENT ({diff} edges)"
            elif shortest:
                tag = "same as shortest"
            else:
                tag = ""

            print(f"    {tolerance:>6} {bw:>6.1f} | {len(route):>6} | {length:>9.0f} | {cost:>10.2f} | {tag}{changed}")
            routes[tolerance] = {'route': route, 'length': length, 'cost': cost}
            prev_route = route

        print(f"\n    Distinct routes: {distinct_routes}")
        if distinct_routes <= 2:
            all_have_gradient = False
            print(f"    ** WARN: Only {distinct_routes} distinct route(s) — still binary! **")
        else:
            print(f"    PASS: {distinct_routes} distinct routes — gradient is working!")

        # Verify accessible route has less barrier cost than shortest
        if 0 in routes and 100 in routes and routes[0]['route'] != routes[100]['route']:
            r0, r100 = routes[0], routes[100]
            if r0['cost'] < r100['cost']:
                print(f"    PASS: Max-avoid route has less barrier cost ({r0['cost']:.2f} < {r100['cost']:.2f})")
            else:
                print(f"    ** WARN: Max-avoid route has MORE barrier cost ({r0['cost']:.2f} >= {r100['cost']:.2f}) **")

    print()
    print("=" * 70)
    if all_have_gradient:
        print("ALL ROUTES SHOW GRADIENT BEHAVIOR")
    else:
        print("SOME ROUTES ARE STILL BINARY — may need tuning")
    print("=" * 70)


def main():
    print("Loading router...")
    router, G_proj = load_router()
    print("Router loaded.\n")

    diagnose_edge_costs(G_proj)
    test_route_divergence(router)


if __name__ == '__main__':
    main()
