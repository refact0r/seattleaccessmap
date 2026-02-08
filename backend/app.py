"""
Flask API server for accessibility routing.

Loads preprocessed data once at startup and provides routing endpoints.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pickle
import pandas as pd
from pathlib import Path
import sys

# Add algorithms to path
sys.path.append(str(Path(__file__).parent))
from algorithms.routing import AccessibilityRouter
from algorithms.clustering import generate_clusters

app = Flask(__name__)
CORS(app)  # Enable CORS for browser requests

# Global router instance and cluster cache
router = None
clusters_cache = None


def load_preprocessed_data():
    """Load preprocessed data structures from disk."""
    global router

    data_dir = Path(__file__).parent / 'data_processed'

    print("Loading preprocessed data...")

    try:
        # Load all components
        with open(data_dir / 'graph.pkl', 'rb') as f:
            graph = pickle.load(f)

        with open(data_dir / 'graph_proj.pkl', 'rb') as f:
            graph_proj = pickle.load(f)

        barriers_df = pd.read_pickle(data_dir / 'barriers.pkl')

        with open(data_dir / 'barrier_tree.pkl', 'rb') as f:
            barrier_tree = pickle.load(f)

        with open(data_dir / 'config.pkl', 'rb') as f:
            config = pickle.load(f)

        # Initialize router
        router = AccessibilityRouter(
            graph, graph_proj, barriers_df, barrier_tree, config
        )

        print(f"✓ Loaded network: {len(graph.nodes):,} nodes, {len(graph.edges):,} edges")
        print(f"✓ Loaded {len(barriers_df):,} barriers")
        print("✓ Router initialized and ready!")

    except FileNotFoundError as e:
        print(f"\n❌ Error: Preprocessed data not found!")
        print(f"   Missing file: {e.filename}")
        print("\n   Please run preprocessing first:")
        print("   python3 backend/preprocess.py\n")
        sys.exit(1)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'message': 'Accessibility routing server is running',
        'router_ready': router is not None
    })


@app.route('/api/barriers', methods=['GET'])
def get_barriers():
    """
    Get barrier data for map visualization.

    Returns:
        JSON array of barriers with lat, lng, severity, label
    """
    if router is None:
        return jsonify({'error': 'Router not initialized'}), 500

    try:
        # Convert barriers dataframe to JSON-friendly format
        barriers_list = []
        for _, row in router.barriers.iterrows():
            barriers_list.append({
                'lat': float(row['lat']),
                'lng': float(row['lon']),
                'severity': int(row['severity']),
                'label': str(row['label'])
            })

        return jsonify(barriers_list)

    except Exception as e:
        print(f"Error getting barriers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clusters', methods=['GET'])
def get_clusters():
    """
    Get HDBSCAN cluster analysis of severe barriers.

    Returns:
        JSON with config, clusters (hotspot metadata), and heatmap_data
    """
    global clusters_cache

    if router is None:
        return jsonify({'error': 'Router not initialized'}), 500

    try:
        # Generate clusters on first request and cache
        if clusters_cache is None:
            print("Generating HDBSCAN clusters (this may take a moment)...")
            clusters_cache = generate_clusters(router.barriers, min_severity=3)
            print(f"✓ Generated {len(clusters_cache['clusters'])} clusters")

        return jsonify(clusters_cache)

    except Exception as e:
        print(f"Error generating clusters: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/calculate_route', methods=['POST'])
def calculate_route():
    """
    Calculate accessibility-aware route.

    Expected JSON body:
    {
        "start_lat": float,
        "start_lng": float,
        "end_lat": float,
        "end_lng": float
    }

    Returns:
        JSON with accessible_route, standard_route, and stats
    """
    if router is None:
        return jsonify({'error': 'Router not initialized'}), 500

    try:
        data = request.json
        start_lat = data['start_lat']
        start_lng = data['start_lng']
        end_lat = data['end_lat']
        end_lng = data['end_lng']

        print(f"Calculating route: ({start_lat}, {start_lng}) → ({end_lat}, {end_lng})")

        result = router.calculate_route(start_lat, start_lng, end_lat, end_lng)

        print(f"✓ Routes calculated successfully")

        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except KeyError as e:
        return jsonify({'error': f'Missing parameter: {e}'}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("ACCESSIBILITY ROUTING API SERVER")
    print("=" * 60)

    load_preprocessed_data()

    print("\n" + "=" * 60)
    print("Starting Flask server on http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=5001, debug=False)
