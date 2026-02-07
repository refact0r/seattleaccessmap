# Backend

## Data Flow

1. **Preprocessing** (run once):
   ```bash
   python preprocess.py
   ```
   - Reads `data/data_clean.csv`
   - Builds data structures (graph, spatial index, etc.)
   - Saves to `data_processed/` (gitignored)

2. **Server** (loads preprocessed data at startup):
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
   - Loads data from `data_processed/` into memory
   - Serves API endpoints on port 5000

## API Endpoints

- `GET /api/health` - Check server status
- `POST /api/route` - Find accessible route (not implemented)
