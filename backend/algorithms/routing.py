"""
Accessibility-aware routing algorithms.

Operates on preprocessed network and barrier data structures.
"""

import networkx as nx
import osmnx as ox
import numpy as np
from scipy.spatial import cKDTree
import json


class AccessibilityRouter:
    """Calculates accessibility-aware routes on Seattle pedestrian network."""

    def __init__(self, graph, graph_proj, barriers_df, barrier_tree, config):
        """
        Initialize router with preprocessed data.

        Args:
            graph: OSMnx graph (unprojected, WGS84)
            graph_proj: OSMnx graph (projected to UTM)
            barriers_df: DataFrame with barrier data
            barrier_tree: cKDTree spatial index for barriers
            config: Dict with routing configuration
        """
        self.G = graph
        self.G_proj = graph_proj
        self.barriers = barriers_df
        self.barrier_tree = barrier_tree
        self.config = config

        # Constants from config
        self.influence_radius = config['barrier_influence_radius']
        self.severity_weight = config['severity_weight']
        self.meters_per_degree = config['meters_per_degree']

    def calculate_route(self, start_lat, start_lng, end_lat, end_lng):
        """
        Calculate both accessible and standard routes.

        Args:
            start_lat, start_lng: Origin coordinates
            end_lat, end_lng: Destination coordinates

        Returns:
            dict with 'accessible_route', 'standard_route', and 'stats'

        Raises:
            ValueError: If no path exists between points
        """
        # Find nearest nodes
        start_node = ox.distance.nearest_nodes(self.G, start_lng, start_lat)
        end_node = ox.distance.nearest_nodes(self.G, end_lng, end_lat)

        # Calculate both routes
        try:
            route_accessible = nx.shortest_path(
                self.G_proj,
                start_node,
                end_node,
                weight='total_cost'
            )

            route_standard = nx.shortest_path(
                self.G_proj,
                start_node,
                end_node,
                weight='length'
            )
        except nx.NetworkXNoPath:
            raise ValueError("No path found between the specified points")

        # Calculate statistics
        accessible_stats = self._calculate_route_stats(route_accessible)
        standard_stats = self._calculate_route_stats(route_standard)

        # Convert to GeoJSON
        accessible_geojson = self._route_to_geojson(route_accessible)
        standard_geojson = self._route_to_geojson(route_standard)

        return {
            'accessible_route': accessible_geojson,
            'standard_route': standard_geojson,
            'stats': {
                'accessible_length': accessible_stats['length'],
                'accessible_barrier_cost': accessible_stats['barrier_cost'],
                'standard_length': standard_stats['length'],
                'standard_barrier_cost': standard_stats['barrier_cost']
            }
        }

    def _calculate_route_stats(self, route):
        """Calculate length and barrier cost for a route."""
        total_length = 0
        total_barrier_cost = 0

        for i in range(len(route) - 1):
            edge_data = self.G_proj[route[i]][route[i+1]][0]
            total_length += edge_data['length']
            total_barrier_cost += edge_data['accessibility_cost']

        return {
            'length': total_length,
            'barrier_cost': total_barrier_cost
        }

    def _route_to_geojson(self, route):
        """Convert route to GeoJSON format."""
        gdf = ox.routing.route_to_gdf(self.G, route)
        return json.loads(gdf.to_json())

    @staticmethod
    def calculate_edge_costs(graph, graph_proj, barriers_df, barrier_tree, config):
        """
        Pre-calculate accessibility costs for all edges.

        This is called during preprocessing and modifies graph_proj in place.

        Args:
            graph: OSMnx graph (unprojected, WGS84)
            graph_proj: OSMnx graph (projected to UTM)
            barriers_df: DataFrame with barrier data
            barrier_tree: cKDTree spatial index for barriers
            config: Dict with routing configuration
        """
        influence_radius = config['barrier_influence_radius']
        severity_weight = config['severity_weight']
        meters_per_degree = config['meters_per_degree']

        print(f"Calculating accessibility costs for {len(graph_proj.edges):,} edges...")

        for u, v, key, data in graph_proj.edges(keys=True, data=True):
            # Get edge midpoint
            u_lat = graph.nodes[u]['y']
            u_lng = graph.nodes[u]['x']
            v_lat = graph.nodes[v]['y']
            v_lng = graph.nodes[v]['x']

            mid_lat = (u_lat + v_lat) / 2
            mid_lng = (u_lng + v_lng) / 2

            # Find nearby barriers
            radius_degrees = influence_radius / meters_per_degree
            nearby_indices = barrier_tree.query_ball_point(
                [mid_lat, mid_lng],
                radius_degrees
            )

            # Calculate accessibility penalty
            if nearby_indices:
                nearby_barriers = barriers_df.iloc[nearby_indices]
                barrier_cost = 0

                for _, barrier in nearby_barriers.iterrows():
                    # Simple distance calculation
                    dist = np.sqrt(
                        (barrier['lat'] - mid_lat)**2 +
                        (barrier['lon'] - mid_lng)**2
                    ) * meters_per_degree

                    if dist < influence_radius:
                        # Inverse distance weighting
                        proximity_factor = 1 - (dist / influence_radius)
                        barrier_cost += barrier['severity'] * proximity_factor

                accessibility_penalty = barrier_cost * severity_weight
            else:
                accessibility_penalty = 0

            # Store costs
            base_length = data.get('length', 0)
            graph_proj[u][v][key]['length'] = base_length
            graph_proj[u][v][key]['accessibility_cost'] = accessibility_penalty
            graph_proj[u][v][key]['total_cost'] = base_length + accessibility_penalty

        print("Edge costs calculated!")
