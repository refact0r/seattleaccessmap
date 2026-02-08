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

    G = deepcopy(G)
    G_proj = deepcopy(G_proj)

    log("calculating edge costs")
    AccessibilityRouter.calculate_edge_costs(
        G, G_proj, barriers_df, barrier_tree, CONFIG
    )

    log("saving outputs")

    with open(DATA_DIR / "graph.pkl", "wb") as f:
        pickle.dump(G, f)

    with open(DATA_DIR / "graph_proj.pkl", "wb") as f:
        pickle.dump(G_proj, f)

    barriers_df.to_pickle(DATA_DIR / "barriers.pkl")

    with open(DATA_DIR / "barrier_tree.pkl", "wb") as f:
        pickle.dump(barrier_tree, f)

    with open(DATA_DIR / "config.pkl", "wb") as f:
        pickle.dump(CONFIG, f)
    log(f"done: {DATA_DIR.absolute()}")


if __name__ == "__main__":
    main()
