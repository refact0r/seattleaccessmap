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

app = Flask(__name__)
CORS(app)  # Enable CORS for browser requests

# Global router instance and cluster data
router = None
clusters_data = None


def load_preprocessed_data():
    """Load preprocessed data structures from disk."""
    global router, clusters_data

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

        with open(data_dir / 'clusters.pkl', 'rb') as f:
            clusters_data = pickle.load(f)

        # Initialize router
        router = AccessibilityRouter(
            graph, graph_proj, barriers_df, barrier_tree, config
        )

        print(f"✓ Loaded network: {len(graph.nodes):,} nodes, {len(graph.edges):,} edges")
        print(f"✓ Loaded {len(barriers_df):,} barriers")
        print(f"✓ Loaded {len(clusters_data['clusters'])} clusters")
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
                'adjusted_severity': round(float(row['adjusted_severity']), 1),
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
    if clusters_data is None:
        return jsonify({'error': 'Cluster data not loaded'}), 500

    return jsonify(clusters_data)


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
        barrier_weight = data.get('barrier_weight', 1.0)  # Default to 1.0 if not provided

        print(f"Calculating route: ({start_lat}, {start_lng}) → ({end_lat}, {end_lng})")
        print(f"  Barrier weight: {barrier_weight:.2f}")

        result = router.calculate_route(start_lat, start_lng, end_lat, end_lng, barrier_weight)

        print(f"✓ Routes calculated successfully")

        return jsonify(result)

    except ValueError as e:
        print(f"ValueError: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
    except KeyError as e:
        print(f"KeyError: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Missing parameter: {e}'}), 400
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
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
