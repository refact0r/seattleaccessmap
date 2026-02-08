"""
Preprocessing script for accessibility routing.

Loads raw data, builds network graph with accessibility costs,
and saves preprocessed data structures to disk for fast server startup.
"""

import osmnx as ox
import pandas as pd
import pickle
from scipy.spatial import cKDTree
from pathlib import Path
import sys

# Add algorithms to path
sys.path.append(str(Path(__file__).parent))
from algorithms.routing import AccessibilityRouter

# Configuration
CONFIG = {
    'barrier_influence_radius': 50,  # meters
    'severity_weight': 1.0,
    'meters_per_degree': 111000,
}

DATA_DIR = Path(__file__).parent / 'data_processed'
DATA_DIR.mkdir(exist_ok=True)


def main():
    print("=" * 60)
    print("ACCESSIBILITY ROUTING - PREPROCESSING")
    print("=" * 60)

    # Load barrier data
    print("\n1. Loading barrier data...")
    barriers_df = pd.read_csv('../data/data_clean.csv')
    barriers_df = barriers_df[barriers_df['severity'].notna()].copy()
    print(f"   Loaded {len(barriers_df):,} barriers with severity ratings")

    # Build spatial index
    print("\n2. Building spatial index for barriers...")
    barrier_coords = barriers_df[['lat', 'lon']].values
    barrier_tree = cKDTree(barrier_coords)
    print(f"   Built spatial index with {len(barrier_coords):,} points")

    # Load Seattle pedestrian network
    print("\n3. Fetching Seattle pedestrian network from OpenStreetMap...")
    print("   (This may take 1-2 minutes on first run, then cached)")

    G = ox.graph_from_place(
        "Seattle, Washington, USA",
        network_type='walk',
        simplify=True
    )
    print(f"   Loaded network: {len(G.nodes):,} nodes, {len(G.edges):,} edges")

    # Project graph
    print("\n4. Projecting graph to UTM...")
    G_proj = ox.project_graph(G)
    print("   Graph projected")

    # Calculate edge accessibility costs
    print("\n5. Calculating accessibility costs for all edges...")
    AccessibilityRouter.calculate_edge_costs(
        G, G_proj, barriers_df, barrier_tree, CONFIG
    )

    # Save preprocessed data
    print("\n6. Saving preprocessed data...")

    # Save graphs
    with open(DATA_DIR / 'graph.pkl', 'wb') as f:
        pickle.dump(G, f)
    print(f"   ✓ Saved graph to {DATA_DIR / 'graph.pkl'}")

    with open(DATA_DIR / 'graph_proj.pkl', 'wb') as f:
        pickle.dump(G_proj, f)
    print(f"   ✓ Saved projected graph to {DATA_DIR / 'graph_proj.pkl'}")

    # Save barrier data
    barriers_df.to_pickle(DATA_DIR / 'barriers.pkl')
    print(f"   ✓ Saved barriers to {DATA_DIR / 'barriers.pkl'}")

    # Save spatial index
    with open(DATA_DIR / 'barrier_tree.pkl', 'wb') as f:
        pickle.dump(barrier_tree, f)
    print(f"   ✓ Saved spatial index to {DATA_DIR / 'barrier_tree.pkl'}")

    # Save config
    with open(DATA_DIR / 'config.pkl', 'wb') as f:
        pickle.dump(CONFIG, f)
    print(f"   ✓ Saved config to {DATA_DIR / 'config.pkl'}")

    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE!")
    print("=" * 60)
    print(f"\nPreprocessed files saved to: {DATA_DIR.absolute()}")
    print("\nYou can now run the Flask server with:")
    print("  cd backend && python3 app.py")
    print("=" * 60)


if __name__ == '__main__':
    main()
