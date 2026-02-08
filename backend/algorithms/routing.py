"""
Accessibility-aware routing algorithms.

Operates on preprocessed network and barrier data structures.
"""

import networkx as nx
import osmnx as ox
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

    def calculate_route(self, start_lat, start_lng, end_lat, end_lng, barrier_weight=1.0):
        """
        Calculate both accessible and standard routes.

        Args:
            start_lat, start_lng: Origin coordinates
            end_lat, end_lng: Destination coordinates
            barrier_weight: How much to penalize barriers (0 = ignore, 10 = max avoid)

        Returns:
            dict with 'accessible_route', 'standard_route', and 'stats'

        Raises:
            ValueError: If no path exists between points
        """
        start_node = ox.distance.nearest_nodes(self.G, start_lng, start_lat)
        end_node = ox.distance.nearest_nodes(self.G, end_lng, end_lat)

        snapped_start = (self.G.nodes[start_node]['y'], self.G.nodes[start_node]['x'])
        snapped_end = (self.G.nodes[end_node]['y'], self.G.nodes[end_node]['x'])

        try:
            if barrier_weight < 0.01:
                route_accessible = nx.shortest_path(
                    self.G_proj, start_node, end_node, weight='length'
                )
            else:
                # On a MultiDiGraph, the weight function receives the dict
                # of parallel edges {key: attr_dict}, not a single edge's
                # attributes. We return the min weight across parallel edges.
                def edge_weight(_u, _v, edge_dict):
                    min_w = float('inf')
                    for key, data in edge_dict.items():
                        length = data.get('length', 0)
                        cost = data.get('accessibility_cost', 0)
                        w = length + barrier_weight * cost * cost
                        min_w = min(min_w, w)
                    return min_w

                route_accessible = nx.shortest_path(
                    self.G_proj, start_node, end_node, weight=edge_weight
                )

            route_standard = nx.shortest_path(
                self.G_proj,
                start_node,
                end_node,
                weight='length'
            )
        except nx.NetworkXNoPath:
            raise ValueError("No path found between the specified points")

        # Weight functions for stats — these operate on individual edge data dicts
        # (not the multigraph edge dict), used by _calculate_route_stats
        def acc_weight(_u, _v, data):
            l = data.get('length', 0)
            c = data.get('accessibility_cost', 0)
            return l + barrier_weight * c * c if barrier_weight >= 0.01 else l

        def std_weight(_u, _v, data):
            return data.get('length', 0)

        accessible_stats = self._calculate_route_stats(route_accessible, acc_weight)
        standard_stats = self._calculate_route_stats(route_standard, std_weight)

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
            },
            'snapped_start': {'lat': snapped_start[0], 'lng': snapped_start[1]},
            'snapped_end': {'lat': snapped_end[0], 'lng': snapped_end[1]}
        }

    def _calculate_route_stats(self, route, weight_fn):
        """Calculate length and barrier cost for a route.

        Uses weight_fn to select the correct edge when parallel edges exist
        (MultiDiGraph), matching the edge Dijkstra actually traversed.
        """
        total_length = 0
        total_barrier_cost = 0

        for i in range(len(route) - 1):
            u, v = route[i], route[i + 1]
            edges = self.G_proj[u][v]
            best_key = min(edges, key=lambda k: weight_fn(u, v, edges[k]))
            edge_data = edges[best_key]
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

        Snaps each barrier point to its nearest edge and accumulates
        severity costs. Every barrier in the dataset contributes to
        exactly one edge.

        Args:
            graph: OSMnx graph (unprojected, WGS84)
            graph_proj: OSMnx graph (projected to UTM)
            barriers_df: DataFrame with barrier data
            barrier_tree: cKDTree spatial index for barriers (unused)
            config: Dict with routing configuration (unused)
        """
        print(f"Snapping {len(barriers_df):,} barriers to nearest edges...")

        # Find nearest edge for each barrier point
        nearest_edges = ox.distance.nearest_edges(
            graph, barriers_df['lon'].values, barriers_df['lat'].values
        )

        # Initialize all edges with zero accessibility cost
        for u, v, key, data in graph_proj.edges(keys=True, data=True):
            data['accessibility_cost'] = 0.0

        # Accumulate barrier severity on nearest edges
        for i in range(len(nearest_edges)):
            u, v, key = int(nearest_edges[i][0]), int(nearest_edges[i][1]), int(nearest_edges[i][2])
            severity = float(barriers_df.iloc[i]['adjusted_severity'])
            if graph_proj.has_edge(u, v, key):
                graph_proj[u][v][key]['accessibility_cost'] += severity

        # Set total_cost
        for u, v, key, data in graph_proj.edges(keys=True, data=True):
            data['total_cost'] = data.get('length', 0) + data['accessibility_cost']

        # Report stats
        costs = [d['accessibility_cost'] for _, _, _, d in graph_proj.edges(keys=True, data=True)]
        nonzero = sum(1 for c in costs if c > 0)
        print(f"Edge costs calculated! {nonzero:,}/{len(costs):,} edges have barriers "
              f"({100*nonzero/len(costs):.1f}%)")
