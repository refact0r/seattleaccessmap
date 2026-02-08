import networkx as nx
import osmnx as ox
import json


class AccessibilityRouter:
    def __init__(self, graph, graph_proj, barriers_df, barrier_tree, config):
        self.G = graph
        self.G_proj = graph_proj
        self.barriers = barriers_df
        self.barrier_tree = barrier_tree
        self.config = config

    def calculate_route(
        self, start_lat, start_lng, end_lat, end_lng, barrier_weight=1.0
    ):
        start_node = ox.distance.nearest_nodes(self.G, start_lng, start_lat)
        end_node = ox.distance.nearest_nodes(self.G, end_lng, end_lat)

        snapped_start = (self.G.nodes[start_node]["y"], self.G.nodes[start_node]["x"])
        snapped_end = (self.G.nodes[end_node]["y"], self.G.nodes[end_node]["x"])

        try:
            if barrier_weight < 0.01:
                route_accessible = nx.shortest_path(
                    self.G_proj, start_node, end_node, weight="length"
                )
            else:
                # multidigraph edge dict contains parallel edges; choose min weight
                def edge_weight(_u, _v, edge_dict):
                    min_w = float("inf")
                    for key, data in edge_dict.items():
                        length = data.get("length", 0)
                        cost = data.get("accessibility_cost", 0)
                        w = length + barrier_weight * cost**1.5
                        min_w = min(min_w, w)
                    return min_w

                route_accessible = nx.shortest_path(
                    self.G_proj, start_node, end_node, weight=edge_weight
                )

            route_standard = nx.shortest_path(
                self.G_proj, start_node, end_node, weight="length"
            )
        except nx.NetworkXNoPath:
            raise ValueError("No path found between the specified points")

        def acc_weight(_u, _v, data):
            l = data.get("length", 0)
            c = data.get("accessibility_cost", 0)
            return l + barrier_weight * c**1.5 if barrier_weight >= 0.01 else l

        def std_weight(_u, _v, data):
            return data.get("length", 0)

        accessible_stats = self._calculate_route_stats(route_accessible, acc_weight)
        standard_stats = self._calculate_route_stats(route_standard, std_weight)

        accessible_geojson = self._route_to_geojson(route_accessible)
        standard_geojson = self._route_to_geojson(route_standard)

        return {
            "accessible_route": accessible_geojson,
            "standard_route": standard_geojson,
            "stats": {
                "accessible_length": accessible_stats["length"],
                "accessible_barrier_cost": accessible_stats["barrier_cost"],
                "accessible_barrier_count": accessible_stats["barrier_count"],
                "standard_length": standard_stats["length"],
                "standard_barrier_cost": standard_stats["barrier_cost"],
                "standard_barrier_count": standard_stats["barrier_count"],
            },
            "snapped_start": {"lat": snapped_start[0], "lng": snapped_start[1]},
            "snapped_end": {"lat": snapped_end[0], "lng": snapped_end[1]},
        }

    def _calculate_route_stats(self, route, weight_fn):
        total_length = 0
        total_barrier_cost = 0
        total_barrier_count = 0

        for i in range(len(route) - 1):
            u, v = route[i], route[i + 1]
            edges = self.G_proj[u][v]
            best_key = min(edges, key=lambda k: weight_fn(u, v, edges[k]))
            edge_data = edges[best_key]
            total_length += edge_data["length"]
            total_barrier_cost += edge_data["accessibility_cost"]
            total_barrier_count += edge_data.get("barrier_count", 0)

        return {
            "length": total_length,
            "barrier_cost": total_barrier_cost,
            "barrier_count": total_barrier_count,
        }

    def _route_to_geojson(self, route):
        gdf = ox.routing.route_to_gdf(self.G, route)
        return json.loads(gdf.to_json())

    @staticmethod
    def calculate_edge_costs(graph, graph_proj, barriers_df, barrier_tree, config):
        nearest_edges = ox.distance.nearest_edges(
            graph, barriers_df["lon"].values, barriers_df["lat"].values
        )

        for u, v, key, data in graph_proj.edges(keys=True, data=True):
            data["accessibility_cost"] = 0.0
            data["barrier_count"] = 0

        for i in range(len(nearest_edges)):
            u, v, key = (
                int(nearest_edges[i][0]),
                int(nearest_edges[i][1]),
                int(nearest_edges[i][2]),
            )
            severity = float(barriers_df.iloc[i]["adjusted_severity"])
            if graph_proj.has_edge(u, v, key):
                graph_proj[u][v][key]["accessibility_cost"] += severity
                graph_proj[u][v][key]["barrier_count"] += 1

        for u, v, key, data in graph_proj.edges(keys=True, data=True):
            data["total_cost"] = data.get("length", 0) + data["accessibility_cost"]
