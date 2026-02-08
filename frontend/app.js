import { initMap } from './map.js'
import { initViewTabs } from './views.js'
import { initBarriers } from './barriers.js'
import { initClusters } from './clusters.js'
import { initPriorities } from './priorities.js'
import { initRouting } from './routing.js'
import { initAnalytics } from './analytics.js'
import { showBackendError } from './errors.js'
import { cssVar, themeColors, severityColor } from './theme.js'

const map = initMap()
const sharedRenderer = L.canvas({ padding: 0.5 })

const barriers = initBarriers({
	map,
	renderer: sharedRenderer,
	severityColor,
	onBackendError: showBackendError,
})

const clusters = initClusters({
	map,
	renderer: sharedRenderer,
	themeColors,
	severityColor,
	onBackendError: showBackendError,
})

let setPrioritiesVisible = () => {}

const priorities = initPriorities({
	map,
	renderer: sharedRenderer,
	onBackendError: showBackendError,
	setPrioritiesVisible: (visible) => setPrioritiesVisible(visible),
})

const routing = initRouting({
	map,
	themeColors,
	setOverlayInteractivity: (enabled) => {
		barriers.setInteractivityEnabled(enabled)
		clusters.setInteractivityEnabled(enabled)
		priorities.setInteractivityEnabled(enabled)
	},
})

const analytics = initAnalytics({ severityColor, cssVar, themeColors })

// Layer toggles

const legendSeverity = document.getElementById('legend-severity')
const legendPriorities = document.getElementById('legend-priorities')
const toggleBarriers = document.getElementById('toggle-barriers')
const toggleHeatmap = document.getElementById('toggle-heatmap')
const toggleClusters = document.getElementById('toggle-clusters')
const togglePriorities = document.getElementById('toggle-priorities')

function updateLegendVisibility() {
	const showSeverityLegend =
		toggleBarriers.checked ||
		toggleClusters.checked ||
		toggleHeatmap.checked
	legendSeverity.classList.toggle('is-hidden', !showSeverityLegend)
	legendPriorities.classList.toggle('is-hidden', !togglePriorities.checked)
}

function setLayerVisibility({ toggleEl, layer, onEnable }) {
	if (toggleEl.checked) {
		map.addLayer(layer)
		if (onEnable) onEnable()
	} else {
		map.removeLayer(layer)
	}
	updateLegendVisibility()
}

toggleBarriers.addEventListener('change', () => {
	setLayerVisibility({
		toggleEl: toggleBarriers,
		layer: barriers.barriersLayer,
		onEnable: () => barriers.applyFilters(),
	})
})

toggleHeatmap.addEventListener('change', () => {
	setLayerVisibility({
		toggleEl: toggleHeatmap,
		layer: clusters.heatmapGroup,
	})
})

toggleClusters.addEventListener('change', () => {
	setLayerVisibility({
		toggleEl: toggleClusters,
		layer: clusters.clustersLayer,
	})
})

togglePriorities.addEventListener('change', () => {
	setLayerVisibility({
		toggleEl: togglePriorities,
		layer: priorities.prioritiesLayer,
	})
})

function setToggleChecked(toggleEl, checked) {
	if (toggleEl.checked === checked) return
	toggleEl.checked = checked
	toggleEl.dispatchEvent(new Event('change'))
}

function applyExplorePreset(preset) {
	if (preset === 'barriers') {
		setToggleChecked(toggleBarriers, true)
		setToggleChecked(toggleHeatmap, false)
		setToggleChecked(toggleClusters, false)
		setToggleChecked(togglePriorities, false)
		return
	}
	if (preset === 'clusters') {
		setToggleChecked(toggleBarriers, false)
		setToggleChecked(toggleHeatmap, false)
		setToggleChecked(toggleClusters, true)
		setToggleChecked(togglePriorities, false)
		return
	}
	if (preset === 'priorities') {
		setToggleChecked(toggleBarriers, false)
		setToggleChecked(toggleHeatmap, false)
		setToggleChecked(toggleClusters, false)
		setToggleChecked(togglePriorities, true)
		return
	}
}

setPrioritiesVisible = (visible) => {
	if (togglePriorities.checked === visible) {
		updateLegendVisibility()
		return
	}
	togglePriorities.checked = visible
	togglePriorities.dispatchEvent(new Event('change'))
}

updateLegendVisibility()

initViewTabs({
	map,
	onAnalyticsOpen: analytics.loadAnalyticsIfNeeded,
	onRouteLeave: routing.resetClickMode,
	onExplorePreset: applyExplorePreset,
})
