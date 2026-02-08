"""
Accessibility-aware routing for Seattle pedestrian network.

Uses OSMnx to fetch the street network and calculates shortest paths that
minimize exposure to accessibility barriers from the Project Sidewalk dataset.
"""

import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

# Configuration
START_LAT, START_LNG = (-122.3321, 47.6062)

END_LAT, END_LNG = (47.6205, -122.3493)

BARRIER_INFLUENCE_RADIUS = 50  # meters - how far a barrier affects nearby edges
SEVERITY_WEIGHT = 1.0  # multiplier for severity impact on edge cost

# Constants
METERS_PER_DEGREE = 111000  # approximate meters per degree of latitude at Earth's surface

# Load the accessibility dataset
print("Loading accessibility data...")
df_barriers = pd.read_csv('data/data_clean.csv')

# Filter to barriers with severity data (already clean, but keeping check)
df_barriers = df_barriers[df_barriers['severity'].notna()].copy()
print(f"Loaded {len(df_barriers):,} accessibility barriers with severity ratings")

# Get Seattle pedestrian network
print("\nFetching Seattle pedestrian network from OpenStreetMap...")
print("(This may take 1-2 minutes on first run, then cached locally)")

# Define Seattle bounding box
place_name = "Seattle, Washington, USA"
G = ox.graph_from_place(
    place_name,
    network_type='walk',  # pedestrian network
    simplify=True
)

print(f"Network loaded: {len(G.nodes):,} nodes, {len(G.edges):,} edges")

# Project graph to UTM for accurate distance calculations
G_proj = ox.project_graph(G)

# Build spatial index for barriers (using WGS84 coordinates)
print("\nBuilding spatial index for barriers...")
barrier_coords = df_barriers[['lat', 'lon']].values
barrier_tree = cKDTree(barrier_coords)

# Add accessibility cost to each edge
print("Calculating accessibility costs for network edges...")

for u, v, key, data in G_proj.edges(keys=True, data=True):
    # Midpoint of edge
    mid_lat = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
    mid_lng = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2

    # Find nearby barriers within influence radius
    # Query using lat/lng coordinates (roughly convert meters to degrees)
    radius_degrees = BARRIER_INFLUENCE_RADIUS / METERS_PER_DEGREE
    nearby_indices = barrier_tree.query_ball_point([mid_lat, mid_lng], radius_degrees)

    # Calculate accessibility penalty
    if nearby_indices:
        nearby_barriers = df_barriers.iloc[nearby_indices]

        # Weight by severity and proximity
        barrier_cost = 0
        for _, barrier in nearby_barriers.iterrows():
            # Simple distance calculation (Haversine would be more accurate but slower)
            dist = np.sqrt(
                (barrier['lat'] - mid_lat)**2 +
                (barrier['lon'] - mid_lng)**2
            ) * METERS_PER_DEGREE  # convert degrees to rough meters

            if dist < BARRIER_INFLUENCE_RADIUS:
                # Inverse distance weighting: closer barriers have more impact
                proximity_factor = 1 - (dist / BARRIER_INFLUENCE_RADIUS)
                barrier_cost += barrier['severity'] * proximity_factor

        accessibility_penalty = barrier_cost * SEVERITY_WEIGHT
    else:
        accessibility_penalty = 0

    # Base cost is edge length, add accessibility penalty
    base_length = data.get('length', 0)
    total_cost = base_length + accessibility_penalty

    # Store both costs for analysis
    G_proj[u][v][key]['length'] = base_length
    G_proj[u][v][key]['accessibility_cost'] = accessibility_penalty
    G_proj[u][v][key]['total_cost'] = total_cost

print("Edge costs calculated!")

# Find nearest nodes to start/end points
print("\nFinding route...")
start_node = ox.distance.nearest_nodes(G, START_LNG, START_LAT)
end_node = ox.distance.nearest_nodes(G, END_LNG, END_LAT)

# Calculate shortest path using total cost (length + accessibility penalty)
try:
    route_accessible = nx.shortest_path(
        G_proj,
        start_node,
        end_node,
        weight='total_cost'
    )

    # Also calculate standard shortest path (distance only)
    route_standard = nx.shortest_path(
        G_proj,
        start_node,
        end_node,
        weight='length'
    )

    # Calculate statistics
    accessible_length = sum(
        G_proj[route_accessible[i]][route_accessible[i+1]][0]['length']
        for i in range(len(route_accessible) - 1)
    )
    accessible_barrier_cost = sum(
        G_proj[route_accessible[i]][route_accessible[i+1]][0]['accessibility_cost']
        for i in range(len(route_accessible) - 1)
    )

    standard_length = sum(
        G_proj[route_standard[i]][route_standard[i+1]][0]['length']
        for i in range(len(route_standard) - 1)
    )
    standard_barrier_cost = sum(
        G_proj[route_standard[i]][route_standard[i+1]][0]['accessibility_cost']
        for i in range(len(route_standard) - 1)
    )

    print("\n" + "="*60)
    print("ROUTING RESULTS")
    print("="*60)
    print(f"\nStart: ({START_LAT:.4f}, {START_LNG:.4f})")
    print(f"End:   ({END_LAT:.4f}, {END_LNG:.4f})")

    print(f"\nAccessibility-Optimized Route:")
    print(f"  Distance: {accessible_length:.0f} m")
    print(f"  Barrier exposure: {accessible_barrier_cost:.1f}")
    print(f"  Nodes: {len(route_accessible)}")

    print(f"\nStandard Shortest Route:")
    print(f"  Distance: {standard_length:.0f} m")
    print(f"  Barrier exposure: {standard_barrier_cost:.1f}")
    print(f"  Nodes: {len(route_standard)}")

    print(f"\nComparison:")
    print(f"  Extra distance: {accessible_length - standard_length:.0f} m ({((accessible_length/standard_length - 1)*100):.1f}%)")
    print(f"  Barrier reduction: {standard_barrier_cost - accessible_barrier_cost:.1f} ({((1 - accessible_barrier_cost/max(standard_barrier_cost, 0.01))*100):.1f}%)")

    # Save routes for visualization
    print("\nSaving routes to output/...")

    # Convert routes to GeoDataFrames
    route_accessible_gdf = ox.routing.route_to_gdf(G, route_accessible)
    route_standard_gdf = ox.routing.route_to_gdf(G, route_standard)

    # Save as GeoJSON
    route_accessible_gdf.to_file('output/route_accessible.geojson', driver='GeoJSON')
    route_standard_gdf.to_file('output/route_standard.geojson', driver='GeoJSON')

    print("✓ Routes saved to output/route_accessible.geojson and output/route_standard.geojson")

except nx.NetworkXNoPath:
    print("\n❌ No path found between the specified points!")
except Exception as e:
    print(f"\n❌ Error calculating route: {e}")

print("\nDone!")
