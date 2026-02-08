from pathlib import Path
import osmnx as ox
import pandas as pd
import pickle
import numpy as np
from copy import deepcopy
from scipy.spatial import cKDTree
import sys

sys.path.append(str(Path(__file__).parent))
from algorithms.routing import AccessibilityRouter
from algorithms.clustering import generate_clusters

CONFIG = {}

DATA_DIR = Path(__file__).parent / "data_processed"
DATA_DIR.mkdir(exist_ok=True)


def main():
    print("=" * 60)
    print("ACCESSIBILITY ROUTING - PREPROCESSING")
    print("=" * 60)

    print("\n1. Loading barrier data...")
    barriers_df = pd.read_csv("../data/data_clean.csv")
    barriers_df = barriers_df[barriers_df["adjusted_severity"].notna()].copy()
    print(f"   Loaded {len(barriers_df):,} barriers with severity ratings")

    print("\n2. Generating HDBSCAN clusters...")
    clusters_data = generate_clusters(barriers_df, min_severity=4)
    with open(DATA_DIR / "clusters.pkl", "wb") as f:
        pickle.dump(clusters_data, f)
    print(f"   ✓ Generated {len(clusters_data['clusters'])} clusters")
    print(f"   ✓ Saved clusters to {DATA_DIR / 'clusters.pkl'}")

    print("\n3. Building spatial index for barriers...")
    mean_lat = barriers_df["lat"].mean()
    cos_lat = np.cos(np.radians(mean_lat))
    CONFIG["cos_lat"] = cos_lat
    print(f"   Latitude correction: cos({mean_lat:.1f}°) = {cos_lat:.4f}")

    barrier_coords = np.column_stack(
        [barriers_df["lat"].values, barriers_df["lon"].values * cos_lat]
    )
    barrier_tree = cKDTree(barrier_coords)
    print(f"   Built spatial index with {len(barrier_coords):,} points")

    raw_graph_path = DATA_DIR / "network_raw.pkl"
    raw_graph_proj_path = DATA_DIR / "network_raw_proj.pkl"

    if raw_graph_path.exists() and raw_graph_proj_path.exists():
        print("\n4. Loading cached pedestrian network from disk...")
        with open(raw_graph_path, "rb") as f:
            G = pickle.load(f)
        print(f"   Loaded network: {len(G.nodes):,} nodes, {len(G.edges):,} edges")

        print("\n5. Loading cached projected graph from disk...")
        with open(raw_graph_proj_path, "rb") as f:
            G_proj = pickle.load(f)
        print("   Loaded projected graph")
    else:
        print("\n4. Fetching Seattle pedestrian network from OpenStreetMap...")
        print("   (This will be cached locally for future runs)")
        G = ox.graph_from_place(
            "Seattle, Washington, USA", network_type="walk", simplify=True
        )
        print(f"   Loaded network: {len(G.nodes):,} nodes, {len(G.edges):,} edges")

        print("\n5. Projecting graph to UTM...")
        G_proj = ox.project_graph(G)
        print("   Graph projected")

        print("   Caching raw network to disk...")
        with open(raw_graph_path, "wb") as f:
            pickle.dump(G, f)
        with open(raw_graph_proj_path, "wb") as f:
            pickle.dump(G_proj, f)
        print(f"   ✓ Cached to {raw_graph_path.name} and {raw_graph_proj_path.name}")

    G = deepcopy(G)
    G_proj = deepcopy(G_proj)

    print("\n6. Calculating accessibility costs for all edges...")
    AccessibilityRouter.calculate_edge_costs(
        G, G_proj, barriers_df, barrier_tree, CONFIG
    )

    print("\n7. Saving preprocessed data...")

    with open(DATA_DIR / "graph.pkl", "wb") as f:
        pickle.dump(G, f)
    print(f"   ✓ Saved graph to {DATA_DIR / 'graph.pkl'}")

    with open(DATA_DIR / "graph_proj.pkl", "wb") as f:
        pickle.dump(G_proj, f)
    print(f"   ✓ Saved projected graph to {DATA_DIR / 'graph_proj.pkl'}")

    barriers_df.to_pickle(DATA_DIR / "barriers.pkl")
    print(f"   ✓ Saved barriers to {DATA_DIR / 'barriers.pkl'}")

    with open(DATA_DIR / "barrier_tree.pkl", "wb") as f:
        pickle.dump(barrier_tree, f)
    print(f"   ✓ Saved spatial index to {DATA_DIR / 'barrier_tree.pkl'}")

    with open(DATA_DIR / "config.pkl", "wb") as f:
        pickle.dump(CONFIG, f)
    print(f"   ✓ Saved config to {DATA_DIR / 'config.pkl'}")

    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE!")
    print("=" * 60)
    print(f"\nPreprocessed files saved to: {DATA_DIR.absolute()}")
    print("\nYou can now run the Flask server with:")
    print("  cd backend && python3 app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
