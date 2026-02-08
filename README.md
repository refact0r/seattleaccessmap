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
  - `adjusted_severity`: 0-10 rescaled severity (see below)

### Adjusted Severity Scale

Raw `severity` (1-5) is rescaled per label type to a 0-10 `adjusted_severity` via linear interpolation: `adj = min + (severity - 1) / 4 × (max - min)`. This accounts for the fact that different barrier types have different baseline impacts:

| Label | Range (min–max) | Rationale |
|-------|----------------|-----------|
| CurbRamp | 0–5 | Positive feature; even sev 5 = problematic but ramp still exists |
| NoCurbRamp | 3–8 | Missing ramp; sev 1 is already a real barrier |
| NoSidewalk | 5–10 | Always significant; no sidewalk at any severity is impactful |
| Obstacle | 2–7 | Obstruction; maps directly to impact |
| SurfaceProblem | 1–6 | Damaged surface; maps directly to impact |
| Other | 1–4 | Miscellaneous (~64 records); low weight |

## Project Structure

```
/
├── backend/                      # Python Flask API server
│   ├── app.py                    # Server (loads preprocessed data at startup)
│   ├── preprocess.py             # Builds network graph + edge costs from CSV
│   ├── test_routing.py           # Routing gradient tests (barrier_weight sweep)
│   ├── requirements.txt          # Flask, OSMnx, pandas, scipy, networkx
│   ├── algorithms/
│   │   ├── routing.py            # AccessibilityRouter class (Dijkstra with barrier costs)
│   │   └── clustering.py         # HDBSCAN hotspot clustering
│   └── data_processed/           # Gitignored - preprocessed artifacts
│       ├── graph.pkl             # OSMnx pedestrian network (WGS84)
│       ├── graph_proj.pkl        # Projected graph (UTM) with edge costs
│       ├── barriers.pkl          # Barrier DataFrame
│       ├── barrier_tree.pkl      # cKDTree spatial index
│       └── config.pkl            # Routing parameters
├── frontend/                     # Web app (plain HTML/JS + Leaflet)
│   └── index.html                # Main UI with routing input panel + tolerance slider
├── data/
│   ├── data.csv                  # Raw dataset (~82k records)
│   ├── data_clean.csv            # Cleaned dataset (79,722 records with severity)
│   ├── neighborhood-incomes.csv  # ACS/Census income data by CRA neighborhood
│   └── neighborhood_lookup.py    # Maps Project Sidewalk neighborhoods → income CRA names
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
- Snaps each barrier to its nearest edge using `ox.distance.nearest_edges` and accumulates severity
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
- Map loads cluster/heatmap overlays and individual barrier points from the backend API
- User enters origin/destination, adjusts barrier tolerance slider → calls `/api/calculate_route` → displays accessible + standard routes

## Routing Algorithm

**Core concept**: Modified Dijkstra's with a user-adjustable `barrier_weight` parameter that controls how aggressively routes avoid barriers.

**Edge cost calculation** (preprocessing):

- Each barrier is snapped to its nearest graph edge via `ox.distance.nearest_edges`
- Edge `accessibility_cost` = sum of `adjusted_severity` values for all barriers snapped to it

**Runtime edge weight** (with barrier_weight `bw`):

- `weight = length + bw × accessibility_cost²`
- The quadratic penalty (`cost²`) produces a gradient of routes across the slider range — low `bw` avoids only the worst edges, high `bw` avoids all barrier edges
- When `bw < 0.01`, falls back to `weight = length` (pure shortest path)

**Barrier tolerance slider** (frontend):

- Slider range: 0 (avoid all barriers) → 100 (ignore barriers)
- Maps to `barrier_weight = (100 - tolerance) / 10`, so tolerance 0 → bw=10, tolerance 100 → bw=0

**Route types**:

- **Accessible route**: Dijkstra with `weight = length + bw × cost²`
- **Standard route**: Dijkstra with `weight = length` (shortest distance)

**Output**: GeoJSON routes + stats (distance, barrier exposure, % tradeoff) + snapped start/end coordinates

---

**Note**: Please keep this file updated when making major changes to the project structure, data flow, or key architectural decisions. This helps both humans and AI agents understand the codebase.
