import { API_BASE_URL } from './config.js'
import { cssVar } from './theme.js'

export function initPriorities({
	map,
	renderer,
	onBackendError,
	setPrioritiesVisible,
}) {
	const prioritiesLayer = L.layerGroup()
	const priorityMarkers = []
	let interactivityEnabled = true
	const toggleEl = document.getElementById('toggle-priorities')

	function ensurePrioritiesLayerVisible() {
		if (typeof setPrioritiesVisible === 'function') {
			setPrioritiesVisible(true)
			return
		}
		if (!map.hasLayer(prioritiesLayer)) map.addLayer(prioritiesLayer)
		if (toggleEl) toggleEl.checked = true
	}

	function parseColorToRgb(color) {
		if (!color) return [0, 0, 0]
		const trimmed = color.trim()
		if (trimmed.startsWith('rgb')) {
			const nums = trimmed.match(/\d+/g) || []
			return nums.slice(0, 3).map((n) => parseInt(n, 10))
		}
		if (trimmed.startsWith('hsl')) {
			const nums = trimmed.match(/-?\d+(?:\.\d+)?/g) || []
			const h = (((parseFloat(nums[0]) || 0) % 360) + 360) % 360
			const s = Math.max(0, Math.min(100, parseFloat(nums[1]) || 0))
			const l = Math.max(0, Math.min(100, parseFloat(nums[2]) || 0))
			const c = (1 - Math.abs(2 * (l / 100) - 1)) * (s / 100)
			const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
			const m = l / 100 - c / 2
			let r = 0
			let g = 0
			let b = 0
			if (h < 60) {
				r = c
				g = x
			} else if (h < 120) {
				r = x
				g = c
			} else if (h < 180) {
				g = c
				b = x
			} else if (h < 240) {
				g = x
				b = c
			} else if (h < 300) {
				r = x
				b = c
			} else {
				r = c
				b = x
			}
			return [
				Math.round((r + m) * 255),
				Math.round((g + m) * 255),
				Math.round((b + m) * 255),
			]
		}
		if (trimmed.startsWith('#')) {
			let hex = trimmed.slice(1)
			if (hex.length === 3) {
				hex = hex
					.split('')
					.map((c) => c + c)
					.join('')
			}
			const num = parseInt(hex, 16)
			return [(num >> 16) & 255, (num >> 8) & 255, num & 255]
		}
		return [0, 0, 0]
	}

	const lowRgb = parseColorToRgb(cssVar('--border', '#d1d5db'))
	const highRgb = parseColorToRgb(cssVar('--accent', '#a78bfa'))

	function impactColor(impact, minImpact, maxImpact) {
		const range = maxImpact - minImpact
		const t = range > 0 ? (impact - minImpact) / range : 1
		const clamped = Math.max(0, Math.min(1, t))
		const r = Math.round(lowRgb[0] + clamped * (highRgb[0] - lowRgb[0]))
		const g = Math.round(lowRgb[1] + clamped * (highRgb[1] - lowRgb[1]))
		const b = Math.round(lowRgb[2] + clamped * (highRgb[2] - lowRgb[2]))
		return `rgb(${r},${g},${b})`
	}

	fetch(`${API_BASE_URL}/api/fix_priorities`)
		.then((r) => r.json())
		.then((data) => {
			if (data.error) {
				console.warn('Fix priorities not available:', data.error)
				return
			}

			const features = data.features || []
			const listEl = document.getElementById('priorities-list')

			const impacts = features
				.map((f) => f.properties && f.properties.impact)
				.filter((v) => typeof v === 'number' && !Number.isNaN(v))
			const minImpact = impacts.length > 0 ? Math.min(...impacts) : 0
			const maxImpact = impacts.length > 0 ? Math.max(...impacts) : 1

			features.forEach((feature) => {
				const props = feature.properties
				const [lng, lat] = feature.geometry.coordinates
				const impact =
					typeof props.impact === 'number' &&
					!Number.isNaN(props.impact)
						? props.impact
						: minImpact
				const color = impactColor(impact, minImpact, maxImpact)

				const street =
					props.street && props.street !== 'unnamed'
						? props.street
						: null
				const popupContent = `
					<div class="popup-card">
						<h4 class="popup-title">Fix Priority #${props.rank}</h4>
						<strong>${props.neighborhood}</strong><br>
						<strong>Impact:</strong> ${props.impact.toFixed(0)}<br>
						<strong>Severity:</strong> ${props.adjusted_severity.toFixed(1)}<br>
						<strong>Type:</strong> ${props.label}<br>
						${street ? `<strong>Street:</strong> ${street}<br>` : ''}
						<div class="popup-divider">
							<strong>Edge usage:</strong> ${props.usage.toLocaleString()} routes
						</div>
					</div>`

				const marker = L.circleMarker([lat, lng], {
					radius: 6,
					color: '#ffffff',
					fillColor: color,
					fillOpacity: 0.9,
					weight: 2,
					interactive: interactivityEnabled,
					renderer,
				})
					.bindPopup(popupContent)
					.addTo(prioritiesLayer)
				priorityMarkers.push(marker)

				if (listEl) {
					const item = document.createElement('div')
					item.className = 'priority-item'
					const detail = street
						? `${props.label} — ${street}`
						: props.label
					item.innerHTML = `
						<span class="priority-rank" style="background:${color}">${props.rank}</span>
						<div class="priority-info">
							<span class="priority-neighborhood">${props.neighborhood}</span>
							<span class="priority-detail">${detail}</span>
						</div>
						<span class="priority-impact">${props.impact.toFixed(0)}</span>`
					item.addEventListener('click', () => {
						ensurePrioritiesLayerVisible()
						map.flyTo([lat, lng], 17)
						marker.openPopup()
					})
					listEl.appendChild(item)
				}
			})
		})
		.catch((err) => {
			console.error('Error loading fix priorities:', err)
			onBackendError()
		})

	function setInteractivityEnabled(enabled) {
		if (interactivityEnabled === enabled) return
		interactivityEnabled = enabled
		for (let i = 0; i < priorityMarkers.length; i++) {
			priorityMarkers[i].options.interactive = enabled
		}
		if (!enabled) map.closePopup()
	}

	return { prioritiesLayer, setInteractivityEnabled }
}
