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
│   ├── preprocess.py             # Build runtime data structures from CSV
│   ├── requirements.txt
│   ├── algorithms/
│   │   └── routing.py            # Routing algorithms (operate on in-memory data)
│   └── data_processed/           # Gitignored - preprocessed artifacts
├── frontend/                     # Web app (plain HTML/JS + Leaflet)
│   ├── index.html                # Main UI
│   ├── app.js                    # Logic for fetching data and rendering map
│   └── style.css
├── data/
│   ├── data.csv                  # Raw dataset
│   └── data_clean.csv            # Cleaned dataset (from scripts/clean.py, used by backend)
├── scripts/
│   └── clean.py                  # Data cleaning
├── reference/                    # Hackathon prompt and other reference files
└── [prototype files]             # analysis.py, index.html, serve.sh, /output
```

### Data Flow

1. **Data cleaning** (one-time): `scripts/clean.py` → `data/data_clean.csv`
2. **Backend preprocessing** (run on setup/changes): `backend/preprocess.py` → `backend/data_processed/*`
3. **Runtime**: `backend/app.py` loads preprocessed data into memory, serves API
4. **Frontend**: Fetches from API, displays on Leaflet map, handles user interactions

---

**Note**: Please keep this file updated when making major changes to the project structure, data flow, or key architectural decisions. This helps both humans and AI agents understand the codebase.
