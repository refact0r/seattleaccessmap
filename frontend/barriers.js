export function initBarriers({ map, renderer, severityColor, onBackendError }) {
	let allBarriers = []
	let allBarrierMarkers = []
	let renderToken = 0
	let interactivityEnabled = true

	const barriersLayer = L.layerGroup().addTo(map)
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
				renderer,
			})
			marker.on('click', () => {
				const content = `<strong>${b.label}</strong><br>Severity: ${b.severity}/5<br>Adjusted: ${b.adjusted_severity}/10`
				barrierPopup
					.setLatLng(marker.getLatLng())
					.setContent(content)
					.openOn(map)
			})
			return { marker, data: b, visible: true }
		})
	}

	function addAllMarkers(markers) {
		const token = ++renderToken
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

	function setMarkerVisibility(markerObj, visible) {
		if (markerObj.visible === visible) return
		markerObj.visible = visible
		markerObj.marker.options.interactive = visible && interactivityEnabled
		markerObj.marker.setStyle({
			opacity: visible ? 1 : 0,
			fillOpacity: visible ? 0.7 : 0,
		})
	}

	function setInteractivityEnabled(enabled) {
		if (interactivityEnabled === enabled) return
		interactivityEnabled = enabled
		for (let i = 0; i < allBarrierMarkers.length; i++) {
			const markerObj = allBarrierMarkers[i]
			markerObj.marker.options.interactive =
				markerObj.visible && interactivityEnabled
		}
		if (!enabled) map.closePopup()
	}

	function applyFilters() {
		const { types, sevMin, sevMax, hideTemp } = getActiveFilters()
		let visibleCount = 0
		for (let i = 0; i < allBarrierMarkers.length; i++) {
			const { data } = allBarrierMarkers[i]
			let visible = true
			if (!types.includes(data.label)) visible = false
			if (data.adjusted_severity < sevMin) visible = false
			if (data.adjusted_severity > sevMax) visible = false
			if (hideTemp && data.is_temporary) visible = false
			if (visible) visibleCount++
			setMarkerVisibility(allBarrierMarkers[i], visible)
		}

		document.getElementById('stat-visible').textContent =
			visibleCount.toLocaleString()
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
	document
		.getElementById('hide-temp')
		.addEventListener('change', scheduleApplyFilters)

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
			addAllMarkers(allBarrierMarkers)
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
		setInteractivityEnabled,
	}
}
