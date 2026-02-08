# Backend - Accessibility Routing API

Flask server that provides accessibility-aware routing using preprocessed Seattle pedestrian network data.

## Setup

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

Required packages: Flask, Flask-CORS, pandas, numpy, scipy, osmnx, networkx

### 2. Run Preprocessing (One-Time)

```bash
python3 preprocess.py
```

This will:
- Load barrier data from `../data/data_clean.csv`
- Download Seattle pedestrian network from OpenStreetMap (cached locally)
- Calculate accessibility costs for ~55,000 edges
- Save preprocessed data to `data_processed/` (~200MB, gitignored)

**Time**: 1-2 minutes on first run, then uses cached OSMnx data.

### 3. Start the Server

```bash
python3 app.py
```

Server will:
- Load preprocessed data from `data_processed/` (~5 seconds)
- Start Flask on `http://localhost:5001`

## API Endpoints

### `GET /api/health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "Accessibility routing server is running",
  "router_ready": true
}
```

### `POST /api/calculate_route`

Calculate accessibility-optimized and standard routes between two points.

**Request body:**
```json
{
  "start_lat": 47.6062,
  "start_lng": -122.3321,
  "end_lat": 47.6205,
  "end_lng": -122.3493
}
```

**Response:**
```json
{
  "accessible_route": { /* GeoJSON */ },
  "standard_route": { /* GeoJSON */ },
  "stats": {
    "accessible_length": 1523.4,
    "accessible_barrier_cost": 12.3,
    "standard_length": 1450.2,
    "standard_barrier_cost": 28.7
  }
}
```

## Architecture

**Data Flow:**
1. `preprocess.py` → Builds graph + calculates edge costs → Saves `.pkl` files
2. `app.py` → Loads `.pkl` files at startup → Serves routing API
3. `algorithms/routing.py` → Contains `AccessibilityRouter` class (Dijkstra's with barrier costs)

**Edge Cost Formula:**
```
total_cost = edge_length + accessibility_penalty

where:
  accessibility_penalty = Σ (severity × proximity_factor) for barriers within 50m
  proximity_factor = 1 - (distance / 50m)
```

Routes are calculated using NetworkX's `shortest_path` with different weight parameters:
- **Accessible route**: `weight='total_cost'` (minimizes barrier exposure)
- **Standard route**: `weight='length'` (shortest distance)
