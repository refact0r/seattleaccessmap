export function initMap() {
	const DEFAULT_MAP_CENTER = [47.6062, -122.3321]
	const DEFAULT_MAP_ZOOM = 13
	const map = L.map('map', {
		zoomControl: false,
		preferCanvas: true,
	})

	L.control.zoom({ position: 'bottomright' }).addTo(map)

	L.tileLayer(
		'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
		{
			attribution:
				'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
			subdomains: 'abcd',
			maxZoom: 20,
		},
	).addTo(map)

	map.setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM)

	return map
}
