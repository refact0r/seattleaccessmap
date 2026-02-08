export function initRouting({ map, themeColors, setOverlayInteractivity }) {
	let clickMode = null
	let originMarker = null
	let destinationMarker = null

	const toleranceSlider = document.getElementById('tolerance-slider')

	function setClickMode(mode) {
		clickMode = mode
		const mapEl = document.getElementById('map')
		const originBtn = document.getElementById('set-origin-btn')
		const destBtn = document.getElementById('set-destination-btn')

		originBtn.classList.toggle('active', clickMode === 'origin')
		destBtn.classList.toggle('active', clickMode === 'destination')
		mapEl.classList.toggle('map-click-cursor', Boolean(clickMode))

		if (setOverlayInteractivity) {
			setOverlayInteractivity(!clickMode)
		}
	}

	// Click-to-set mode
	document.getElementById('set-origin-btn').addEventListener('click', () => {
		setClickMode(clickMode === 'origin' ? null : 'origin')
	})

	document
		.getElementById('set-destination-btn')
		.addEventListener('click', () => {
			setClickMode(clickMode === 'destination' ? null : 'destination')
		})

	function createMarkerIcon(variant) {
		return L.divIcon({
			className: `custom-marker custom-marker--${variant}`,
			html: '<div class="marker-dot"></div>',
			iconSize: [20, 20],
			iconAnchor: [10, 10],
		})
	}

	map.on('click', (e) => {
		if (!clickMode) return

		const lat = e.latlng.lat.toFixed(4)
		const lng = e.latlng.lng.toFixed(4)

		if (clickMode === 'origin') {
			document.getElementById('start-lat').value = lat
			document.getElementById('start-lng').value = lng
			if (originMarker) map.removeLayer(originMarker)
			originMarker = L.marker([e.latlng.lat, e.latlng.lng], {
				icon: createMarkerIcon('origin'),
			}).addTo(map)
			setClickMode(null)
		} else if (clickMode === 'destination') {
			document.getElementById('end-lat').value = lat
			document.getElementById('end-lng').value = lng
			if (destinationMarker) map.removeLayer(destinationMarker)
			destinationMarker = L.marker([e.latlng.lat, e.latlng.lng], {
				icon: createMarkerIcon('destination'),
			}).addTo(map)
			setClickMode(null)
		}
	})

	function updateMarkers() {
		const sLat = parseFloat(document.getElementById('start-lat').value)
		const sLng = parseFloat(document.getElementById('start-lng').value)
		const eLat = parseFloat(document.getElementById('end-lat').value)
		const eLng = parseFloat(document.getElementById('end-lng').value)

		if (!isNaN(sLat) && !isNaN(sLng)) {
			if (originMarker) map.removeLayer(originMarker)
			originMarker = L.marker([sLat, sLng], {
				icon: createMarkerIcon('origin'),
			}).addTo(map)
		}
		if (!isNaN(eLat) && !isNaN(eLng)) {
			if (destinationMarker) map.removeLayer(destinationMarker)
			destinationMarker = L.marker([eLat, eLng], {
				icon: createMarkerIcon('destination'),
			}).addTo(map)
		}
	}

	function setExample1() {
		document.getElementById('start-lat').value = 47.6551
		document.getElementById('start-lng').value = -122.3046
		document.getElementById('end-lat').value = 47.6305
		document.getElementById('end-lng').value = -122.3566
		updateMarkers()
	}

	function setExample2() {
		document.getElementById('start-lat').value = 47.6552
		document.getElementById('start-lng').value = -122.3045
		document.getElementById('end-lat').value = 47.6205
		document.getElementById('end-lng').value = -122.3212
		updateMarkers()
	}

	document
		.getElementById('calculate-btn')
		.addEventListener('click', async () => {
			const startLat = parseFloat(
				document.getElementById('start-lat').value,
			)
			const startLng = parseFloat(
				document.getElementById('start-lng').value,
			)
			const endLat = parseFloat(document.getElementById('end-lat').value)
			const endLng = parseFloat(document.getElementById('end-lng').value)

			if (
				isNaN(startLat) ||
				isNaN(startLng) ||
				isNaN(endLat) ||
				isNaN(endLng)
			) {
				showStatus('Please enter valid coordinates', 'error')
				return
			}

			const btn = document.getElementById('calculate-btn')
			btn.disabled = true
			btn.textContent = 'Calculating...'
			showStatus('Calculating routes...', 'loading')

			try {
				const tolerance = parseInt(toleranceSlider.value)
				const barrierWeight = (100 - tolerance) / 5

				const response = await fetch(
					'http://localhost:5001/api/calculate_route',
					{
						method: 'POST',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({
							start_lat: startLat,
							start_lng: startLng,
							end_lat: endLat,
							end_lng: endLng,
							barrier_weight: barrierWeight,
						}),
					},
				)

				if (!response.ok)
					throw new Error(`Server error: ${response.statusText}`)

				const data = await response.json()

				if (data.snapped_start) {
					if (originMarker) map.removeLayer(originMarker)
					originMarker = L.marker(
						[data.snapped_start.lat, data.snapped_start.lng],
						{
							icon: createMarkerIcon('origin'),
						},
					)
						.addTo(map)
						.bindPopup('Route Start')
				}
				if (data.snapped_end) {
					if (destinationMarker) map.removeLayer(destinationMarker)
					destinationMarker = L.marker(
						[data.snapped_end.lat, data.snapped_end.lng],
						{
							icon: createMarkerIcon('destination'),
						},
					)
						.addTo(map)
						.bindPopup('Route End')
				}

				if (window.accessibleRouteLayer)
					map.removeLayer(window.accessibleRouteLayer)
				if (window.standardRouteLayer)
					map.removeLayer(window.standardRouteLayer)

				window.accessibleRouteLayer = L.geoJSON(data.accessible_route, {
					style: {
						color: themeColors.routeAccessible,
						weight: 5,
						opacity: 0.8,
					},
				}).addTo(map)

				window.standardRouteLayer = L.geoJSON(data.standard_route, {
					style: {
						color: themeColors.routeStandard,
						weight: 5,
						opacity: 0.8,
					},
				}).addTo(map)

				displayRouteStats(data.stats)

				const allBounds = L.featureGroup([
					window.accessibleRouteLayer,
					window.standardRouteLayer,
				]).getBounds()
				map.fitBounds(allBounds, { padding: [50, 50] })

				showStatus('Routes calculated!', 'success')
			} catch (error) {
				console.error('Error calculating route:', error)
				showStatus(
					'Error: Make sure backend is running (python3 backend/app.py)',
					'error',
				)
			} finally {
				btn.disabled = false
				btn.textContent = 'Calculate Route'
			}
		})

	function showStatus(message, type) {
		const statusDiv = document.getElementById('status-message')
		statusDiv.textContent = message
		statusDiv.className = `status-message ${type}`
		if (type === 'success') {
			setTimeout(() => {
				statusDiv.textContent = ''
				statusDiv.className = ''
			}, 3000)
		}
	}

	function displayRouteStats(stats) {
		const resultsDiv = document.getElementById('route-results')
		const routeContent = document.getElementById('route-content')

		const extraDistance = stats.accessible_length - stats.standard_length
		const extraPercent = (
			(stats.accessible_length / stats.standard_length - 1) *
			100
		).toFixed(1)
		const barrierReduction = (
			((stats.standard_barrier_cost - stats.accessible_barrier_cost) /
				Math.max(stats.standard_barrier_cost, 0.01)) *
			100
		).toFixed(1)
		const barrierCountDiff =
			(stats.standard_barrier_count || 0) -
			(stats.accessible_barrier_count || 0)

		routeContent.innerHTML = `
			<div class="route-stats-row">
				<div class="route-stats">
					<h4>
						<div class="color-dot route-dot-accessible"></div>
						Accessible
					</h4>
					<p>Distance: ${stats.accessible_length.toFixed(0)} m</p>
					<p>Barrier cost: ${stats.accessible_barrier_cost.toFixed(1)}</p>
					<p>Barriers: ${stats.accessible_barrier_count || 0}</p>
				</div>
				<div class="route-stats">
					<h4>
						<div class="color-dot route-dot-standard"></div>
						Standard
					</h4>
					<p>Distance: ${stats.standard_length.toFixed(0)} m</p>
					<p>Barrier cost: ${stats.standard_barrier_cost.toFixed(1)}</p>
					<p>Barriers: ${stats.standard_barrier_count || 0}</p>
				</div>
			</div>
			<div class="comparison">
				<h4>Trade-off Analysis</h4>
				<p>Extra distance: ${extraDistance.toFixed(0)} m (${extraPercent > 0 ? '+' : ''}${extraPercent}%)</p>
				<p>Barrier reduction: ${barrierReduction}%</p>
				<p>Barriers avoided: ${barrierCountDiff}</p>
			</div>`

		resultsDiv.classList.remove('is-hidden')
	}

	// Keep inline example links working.
	window.setExample1 = setExample1
	window.setExample2 = setExample2

	return {
		resetClickMode: () => setClickMode(null),
	}
}
