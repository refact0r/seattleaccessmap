# seattleAccessMap

seattleAccessMap is an accessibility data visualization and routing tool for Seattle. It uses the [Project Sidewalk](https://sidewalk-sea.cs.washington.edu/) Seattle dataset, which consists of ~80,000 crowdsourced observations of accessibility barriers such as missing curb ramps, broken surfaces, obstacles, and missing sidewalks.

The project won 1st place in the 2026 DubsTech Datathon in the Access to Everyday Life track.

<https://refact0r.github.io/seattleaccessmap/>

<img width="1870" height="1010" alt="Screenshot 2026-02-08 at 19-21-17 seattleAccessMap" src="https://github.com/user-attachments/assets/42a00443-c3c3-4746-a0a4-7dde36f3bfd9" />

## Features

### Barrier Visualization

An interactive map of all ~80k barriers across Seattle. Users can filter by barrier type, severity, and temporary/permanent status. Overlays include a severity heatmap and hotspot clusters created using HDBSCAN that highlight concentrated problem areas.

### Fix Prioritization

A ranked list of barriers that would have the most positive impact if repaired. Barriers are scored by both severity and estimated pedestrian traffic (approximated via sampled shortest paths).

### Accessibility-Aware Routing

A route-planning tool that finds paths between two points while minimizing exposure to accessibility barriers. It's built on a modified Dijkstra's algorithm over the real Seattle pedestrian network (via OSMnx). A tolerance slider lets users control the tradeoff between shortest distance and barrier avoidance.

## Setup

### Prereqs

- Python 3.9+
- A browser

### Install dependencies

```bash
pip install -r backend/requirements.txt
```

### Preprocess data

These steps only need to be run once. They clean the dataset, build the routing graph, and generate all static JSON files served by the frontend.

```bash
# 1. Clean the raw dataset
python scripts/clean.py

# 2. Build routing graph, clusters, and export frontend data
cd backend
python analysis/analyze_fix_priority.py
python preprocess.py
```

Preprocessing downloads the Seattle pedestrian network from OpenStreetMap via OSMnx (cached after the first run) and takes a few minutes.

### Run locally

The frontend is fully static, no backend server is needed at runtime.

```bash
# From the project root
python -m http.server 8000
```

Then open <http://localhost:8000/frontend/index.html>.
