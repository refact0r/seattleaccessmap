import { apiFetch } from './config.js'

export function initRouting({ map, themeColors, setOverlayInteractivity }) {
	let clickMode = null
	let originMarker = null
	let destinationMarker = null

	const toleranceSlider = document.getElementById('tolerance-slider')
	const prefersReducedMotion = window.matchMedia(
		'(prefers-reduced-motion: reduce)',
	).matches
	const routeRenderer = L.canvas()
	routeRenderer.addTo(map)

	function extractRouteCoords(geojson) {
		if (!geojson) return []

		const coords = []
		const push = (coord) => {
			if (!coord || coord.length < 2) return
			const latLng = [coord[1], coord[0]]
			const last = coords[coords.length - 1]
			if (!last || last[0] !== latLng[0] || last[1] !== latLng[1]) {
				coords.push(latLng)
			}
		}

		const addGeometry = (geometry) => {
			if (!geometry) return
			if (geometry.type === 'LineString') {
				geometry.coordinates.forEach(push)
				return
			}
			if (geometry.type === 'MultiLineString') {
				geometry.coordinates.forEach((line) => line.forEach(push))
			}
		}

		if (geojson.type === 'FeatureCollection') {
			geojson.features.forEach((feature) => addGeometry(feature.geometry))
		} else if (geojson.type === 'Feature') {
			addGeometry(geojson.geometry)
		} else {
			addGeometry(geojson)
		}

		return coords
	}

	function animateRouteCoords(layer, coords) {
		if (!layer || !coords || coords.length < 2) return
		if (prefersReducedMotion) {
			layer.setLatLngs(coords)
			return
		}

		let totalLength = 0
		const cumulative = [0]
		for (let i = 1; i < coords.length; i += 1) {
			totalLength += map.distance(coords[i - 1], coords[i])
			cumulative[i] = totalLength
		}
		const duration = totalLength * 0.3

		const start = performance.now()
		const tick = (now) => {
			const elapsed = now - start
			const t = Math.min(elapsed / duration, 1)
			const targetDist = totalLength * t

			let idx = 1
			while (idx < cumulative.length && cumulative[idx] < targetDist) {
				idx += 1
			}

			const current = coords.slice(0, Math.min(idx + 1, coords.length))
			if (idx < coords.length) {
				const prevDist = cumulative[idx - 1] || 0
				const segLength =
					cumulative[idx] - prevDist ||
					map.distance(coords[idx - 1], coords[idx])
				const segT =
					segLength > 0 ? (targetDist - prevDist) / segLength : 0
				const startPt = coords[idx - 1]
				const endPt = coords[idx]
				const interp = [
					startPt[0] + (endPt[0] - startPt[0]) * segT,
					startPt[1] + (endPt[1] - startPt[1]) * segT,
				]
				current[current.length - 1] = interp
			}

			layer.setLatLngs(current)
			if (t < 1) {
				requestAnimationFrame(tick)
			} else {
				layer.setLatLngs(coords)
			}
		}

		requestAnimationFrame(tick)
	}

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

				const response = await apiFetch('/api/calculate_route', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						start_lat: startLat,
						start_lng: startLng,
						end_lat: endLat,
						end_lng: endLng,
						barrier_weight: barrierWeight,
					}),
				})

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

				const accessibleCoords = extractRouteCoords(
					data.accessible_route,
				)
				const standardCoords = extractRouteCoords(data.standard_route)

				window.accessibleRouteLayer =
					accessibleCoords.length > 1
						? L.polyline(accessibleCoords, {
								color: themeColors.routeAccessible,
								weight: 5,
								opacity: 0.8,
								className: 'route-path route-path--accessible',
								renderer: routeRenderer,
							}).addTo(map)
						: null

				window.standardRouteLayer =
					standardCoords.length > 1
						? L.polyline(standardCoords, {
								color: themeColors.routeStandard,
								weight: 5,
								opacity: 0.8,
								className: 'route-path route-path--standard',
								renderer: routeRenderer,
							}).addTo(map)
						: null

				const allBounds = L.latLngBounds(
					accessibleCoords.concat(standardCoords),
				)
				displayRouteStats(data.stats)

				map.fitBounds(allBounds, { padding: [50, 50] })

				let didAnimate = false
				const runAnimations = () => {
					if (didAnimate) return
					didAnimate = true
					animateRouteCoords(
						window.accessibleRouteLayer,
						accessibleCoords,
					)
					animateRouteCoords(
						window.standardRouteLayer,
						standardCoords,
					)
				}

				map.once('moveend', runAnimations)
				setTimeout(runAnimations, 160)
				showStatus('Routes calculated!', 'success')
			} catch (error) {
				console.error('Error calculating route:', error)
				showStatus('Error: Make sure backend is reachable', 'error')
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

	window.setExample1 = setExample1
	window.setExample2 = setExample2

	return {
		resetClickMode: () => setClickMode(null),
	}
}
