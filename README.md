# DubsTech Datathon Project: City Accessibility Analysis

## Overview

Hackathon project using the **Project Sidewalk Seattle Accessibility Dataset** (~82k crowdsourced observations of sidewalk conditions). The goal is to both analyze the data, create a map visualization, and most importantly to build a routing tool that finds alternative accessible paths that minimize exposure to accessibility barriers for people with mobility challenges.

Hackathon prompt: `reference/access-to-everyday-life.md`. We're deviating a little from the prompt's questions (we just want to make a cool project) but still addressing the core themes.

## Dataset

- Location: `data/data_clean.csv` (`data/data.csv` is the raw dataset)
- Records: 79,722 (dropped 2,251 rows with missing severity ratings)
- Columns:
  - `lon`, `lat` - coordinates
  - `id` - unique observation ID
  - `label` - 7 types: `CurbRamp`, `NoCurbRamp`, `NoSidewalk`, `Obstacle`, `SurfaceProblem`, `Other`
  - `neighborhood`: 50 neighborhoods of Seattle
  - `severity`: 1-5 scale (guaranteed to be present in the cleaned dataset)
  - `is_temporary`: boolean (~771 are TRUE, rest FALSE)

## Project Structure

```
/
├── backend/                      # Python Flask API server
│   ├── app.py                    # Server (loads preprocessed data at startup)
│   ├── preprocess.py             # Builds network graph + edge costs from CSV
│   ├── requirements.txt          # Flask, OSMnx, pandas, scipy, networkx
│   ├── algorithms/
│   │   └── routing.py            # AccessibilityRouter class (Dijkstra with barrier costs)
│   └── data_processed/           # Gitignored - preprocessed artifacts
│       ├── graph.pkl             # OSMnx pedestrian network (WGS84)
│       ├── graph_proj.pkl        # Projected graph (UTM) with edge costs
│       ├── barriers.pkl          # Barrier DataFrame
│       ├── barrier_tree.pkl      # cKDTree spatial index
│       └── config.pkl            # Routing parameters
├── frontend/                     # Web app (plain HTML/JS + Leaflet)
│   └── index.html                # Main UI with routing input panel
├── data/
│   ├── data.csv                  # Raw dataset (~82k records)
│   └── data_clean.csv            # Cleaned dataset (79,722 records with severity)
├── scripts/
│   └── clean.py                  # Data cleaning
├── output/                       # Analysis visualizations (from analysis.py)
│   ├── clusters_data.json        # HDBSCAN hotspot clusters (for map overlay)
│   ├── heatmap_data.json         # Severity heatmap points (for map overlay)
│   └── *.png                     # Static charts (EDA, clusters, etc.)
├── reference/                    # Hackathon prompt
├── archived/                     # Old prototype files (superseded by backend/)
│   ├── accessibility_routing.py  # Monolithic routing script
│   ├── routing_server.py         # Old Flask server
│   └── index.html                # Old map interface
├── analysis.py                   # Cluster analysis script (generates output/)
└── serve.sh                      # Start local HTTP server
```

### Data Flow

**Phase 1: Data Preparation** (one-time)

```bash
scripts/clean.py  # data.csv → data_clean.csv
python3 analysis.py  # → output/*.json, output/*.png (clusters, heatmaps)
```

**Phase 2: Backend Setup** (one-time)

```bash
cd backend
python3 preprocess.py  # → data_processed/*.pkl (network graph + edge costs)
```

- Loads `data/data_clean.csv` + OSMnx Seattle walk network
- Calculates accessibility cost for every edge (barrier proximity × severity)
- Saves preprocessed routing structures to `data_processed/*.pkl` (~200MB)

**Phase 3: Runtime**

```bash
# Terminal 1: Start routing API
python3 backend/app.py  # Loads .pkl files, serves on :5001

# Terminal 2: Start web server
./serve.sh  # or: python3 -m http.server 8000
```

**Frontend Usage**:

- Open `http://localhost:8000/frontend/index.html`
- Map loads static cluster/heatmap overlays from `/output`
- User enters origin/destination → calls `/api/calculate_route` → displays dynamic routes

## Routing Algorithm

**Core concept**: Modified Dijkstra's that minimizes `total_cost = edge_length + accessibility_penalty`

**Edge cost calculation** (preprocessing):

- For each edge midpoint, find barriers within 50m radius
- For each nearby barrier: `penalty += severity × (1 - distance/50m)` (inverse distance weighting)
- Store `total_cost = length + penalty` on every edge

**Route types**:

- **Accessible route**: Dijkstra with `weight='total_cost'` (minimizes barrier exposure)
- **Standard route**: Dijkstra with `weight='length'` (shortest distance)

**Output**: GeoJSON routes + stats (distance, barrier exposure, % tradeoff)

---

**Note**: Please keep this file updated when making major changes to the project structure, data flow, or key architectural decisions. This helps both humans and AI agents understand the codebase.
