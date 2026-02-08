import { initMap } from './map.js'
import { initViewTabs } from './views.js'
import { initBarriers } from './barriers.js'
import { initClusters } from './clusters.js'
import { initRouting } from './routing.js'
import { initAnalytics } from './analytics.js'
import { showBackendError } from './errors.js'
import { cssVar, themeColors, severityColor } from './theme.js'

const map = initMap()

const barriers = initBarriers({
	map,
	severityColor,
	onBackendError: showBackendError,
})

const clusters = initClusters({
	map,
	themeColors,
	severityColor,
	onBackendError: showBackendError,
})

initRouting({
	map,
	themeColors,
	setOverlayInteractivity: (enabled) => {
		barriers.setInteractivityEnabled(enabled)
		clusters.setInteractivityEnabled(enabled)
	},
})

const analytics = initAnalytics({ severityColor, cssVar, themeColors })

initViewTabs({
	map,
	onAnalyticsOpen: analytics.loadAnalyticsIfNeeded,
})

// Layer toggles

document.getElementById('toggle-barriers').addEventListener('change', (e) => {
	if (e.target.checked) {
		map.addLayer(barriers.barriersLayer)
		barriers.applyFilters()
	} else {
		map.removeLayer(barriers.barriersLayer)
	}
})

document.getElementById('toggle-heatmap').addEventListener('change', (e) => {
	if (e.target.checked) {
		map.addLayer(clusters.heatmapGroup)
	} else {
		map.removeLayer(clusters.heatmapGroup)
	}
})

document.getElementById('toggle-clusters').addEventListener('change', (e) => {
	if (e.target.checked) {
		map.addLayer(clusters.clustersLayer)
	} else {
		map.removeLayer(clusters.clustersLayer)
	}
})
