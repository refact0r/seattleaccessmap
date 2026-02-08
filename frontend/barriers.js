export function initBarriers({ map, severityColor, onBackendError }) {
	let allBarriers = []
	let allBarrierMarkers = []
	let renderToken = 0

	const barriersLayer = L.layerGroup().addTo(map)
	const barrierRenderer = L.canvas({ padding: 0.5 })
	const barrierPopup = L.popup({ closeButton: true })

	function buildBarrierMarkers(barriers) {
		allBarrierMarkers = barriers.map((b) => {
			const c = severityColor(b.adjusted_severity)
			const marker = L.circleMarker([b.lat, b.lng], {
				radius: 2,
				color: c,
				fillColor: c,
				fillOpacity: 0.7,
				weight: 0,
				renderer: barrierRenderer,
			})
			marker.on('click', () => {
				const content = `<strong>${b.label}</strong><br>Severity: ${b.severity}/5<br>Adjusted: ${b.adjusted_severity}/10`
				barrierPopup
					.setLatLng(marker.getLatLng())
					.setContent(content)
					.openOn(map)
			})
			return { marker, data: b }
		})
	}

	function renderBarriers(markers) {
		const token = ++renderToken
		barriersLayer.clearLayers()
		const chunkSize = 1500
		let i = 0

		function addChunk() {
			if (token !== renderToken) return
			const end = Math.min(i + chunkSize, markers.length)
			for (; i < end; i++) {
				markers[i].marker.addTo(barriersLayer)
			}

			if (i < markers.length) {
				requestAnimationFrame(addChunk)
			} else {
				document.getElementById('stat-visible').textContent =
					markers.length.toLocaleString()
			}
		}

		addChunk()
	}

	function getActiveFilters() {
		const types = []
		document.querySelectorAll('[data-type]').forEach((cb) => {
			if (cb.checked) types.push(cb.dataset.type)
		})
		const sevMin = parseFloat(document.getElementById('sev-min').value)
		const sevMax = parseFloat(document.getElementById('sev-max').value)
		const hideTemp = document.getElementById('hide-temp').checked
		return { types, sevMin, sevMax, hideTemp }
	}

	function applyFilters() {
		const { types, sevMin, sevMax, hideTemp } = getActiveFilters()
		const filteredMarkers = []
		for (let i = 0; i < allBarrierMarkers.length; i++) {
			const { data } = allBarrierMarkers[i]
			if (!types.includes(data.label)) continue
			if (data.adjusted_severity < sevMin) continue
			if (data.adjusted_severity > sevMax) continue
			if (hideTemp && data.is_temporary) continue
			filteredMarkers.push(allBarrierMarkers[i])
		}
		// Avoid heavy re-rendering when layer is hidden
		if (map.hasLayer(barriersLayer)) {
			renderBarriers(filteredMarkers)
		} else {
			document.getElementById('stat-visible').textContent =
				filteredMarkers.length.toLocaleString()
		}
	}

	let filterTimer = null
	function scheduleApplyFilters() {
		if (filterTimer) clearTimeout(filterTimer)
		filterTimer = setTimeout(() => {
			filterTimer = null
			applyFilters()
		}, 120)
	}

	// Severity slider display update
	document.getElementById('sev-min').addEventListener('input', (e) => {
		const val = parseFloat(e.target.value)
		const maxSlider = document.getElementById('sev-max')
		if (val > parseFloat(maxSlider.value)) maxSlider.value = val
		document.getElementById('sev-min-val').textContent = val
		document.getElementById('sev-max-val').textContent = maxSlider.value
		scheduleApplyFilters()
	})

	document.getElementById('sev-max').addEventListener('input', (e) => {
		const val = parseFloat(e.target.value)
		const minSlider = document.getElementById('sev-min')
		if (val < parseFloat(minSlider.value)) minSlider.value = val
		document.getElementById('sev-max-val').textContent = val
		document.getElementById('sev-min-val').textContent = minSlider.value
		scheduleApplyFilters()
	})
	document.getElementById('sev-min').addEventListener('change', applyFilters)
	document.getElementById('sev-max').addEventListener('change', applyFilters)

	// Checkbox & toggle listeners
	document.querySelectorAll('[data-type]').forEach((cb) => {
		cb.addEventListener('change', scheduleApplyFilters)
	})
	document.getElementById('hide-temp').addEventListener('change', scheduleApplyFilters)

	fetch('http://localhost:5001/api/barriers')
		.then((r) => r.json())
		.then((barriers) => {
			allBarriers = barriers
			document.getElementById('stat-total').textContent =
				barriers.length.toLocaleString()

			const avgSev =
				barriers.reduce((s, b) => s + b.adjusted_severity, 0) /
				barriers.length
			document.getElementById('stat-avg-sev').textContent =
				avgSev.toFixed(1)

			buildBarrierMarkers(barriers)
			applyFilters()
			console.log(`Loaded ${barriers.length} barrier points`)
		})
		.catch((err) => {
			console.error('Error loading barriers:', err)
			onBackendError()
		})

	return {
		barriersLayer,
		applyFilters,
	}
}
