export function initClusters({
	map,
	themeColors,
	severityColor,
	onBackendError,
}) {
	const heatmapGroup = L.layerGroup()
	const clustersLayer = L.layerGroup()
	const DEFAULT_MAP_CENTER = [47.6062, -122.3321]
	const DEFAULT_MAP_ZOOM = 13

	fetch('http://localhost:5001/api/clusters')
		.then((r) => r.json())
		.then((data) => {
			const { config, clusters, heatmap_data } = data
			const center = (config && config.center) || DEFAULT_MAP_CENTER
			const zoom = (config && config.zoom_start) || DEFAULT_MAP_ZOOM
			map.setView(center, zoom)

			const heatmapLayer = L.heatLayer(
				heatmap_data.map(([lat, lng, severity]) => [lat, lng, severity]),
				{
					radius: 6,
					blur: 10,
					max: 1.0,
					gradient: themeColors.heatmapGradient,
				},
			)
			heatmapGroup.addLayer(heatmapLayer)

			clusters.forEach((cluster) => {
				const clusterColor = severityColor(cluster.mean_severity)
				const typeBreakdownHTML = Object.entries(cluster.type_breakdown)
					.map(([type, count]) => `${type}: ${count}`)
					.join('<br>')

				const popupContent = `
					<div class="popup-card">
						<h4 class="popup-title">Hotspot #${cluster.rank}</h4>
						<strong>${cluster.neighborhood}</strong><br>
						<strong>Issues:</strong> ${cluster.count}<br>
						<strong>Mean severity:</strong> ${cluster.mean_severity.toFixed(1)}<br>
						<strong>Spread:</strong> ${cluster.spread_m.toFixed(0)}m<br>
						<div class="popup-divider">
							<strong>Breakdown:</strong><br>
							${typeBreakdownHTML}
						</div>
					</div>`

				cluster.points.forEach((pt) => {
					L.circleMarker([pt.lat, pt.lng], {
						radius: 2,
						color: clusterColor,
						fillColor: clusterColor,
						fillOpacity: 0.7,
						weight: 1,
					})
						.bindPopup(popupContent)
						.addTo(clustersLayer)
				})
			})

			console.log(`Loaded ${clusters.length} clusters`)
		})
		.catch((err) => {
			console.error('Error loading clusters:', err)
			onBackendError()
		})

	return { heatmapGroup, clustersLayer }
}
