export function initViewTabs({
	map,
	onAnalyticsOpen,
	onRouteLeave,
	onExplorePreset,
}) {
	const navTabs = document.querySelectorAll('.nav-tab')
	const viewContents = document.querySelectorAll('.view-content')
	const content = document.querySelector('.content')

	function switchTo(viewId) {
		// Update tab state
		navTabs.forEach((t) => t.classList.remove('active'))
		document
			.querySelector(`.nav-tab[data-view="${viewId}"]`)
			?.classList.add('active')

		// Update panel content
		viewContents.forEach((v) => v.classList.remove('active'))
		document.getElementById('view-' + viewId)?.classList.add('active')

		// Toggle full-width layout for views that don't use the map
		content.classList.toggle(
			'panel-full',
			viewId === 'about' || viewId === 'analytics'
		)

		// View-specific actions
		if (viewId === 'analytics') {
			onAnalyticsOpen()
		}
		if (viewId !== 'route' && onRouteLeave) {
			onRouteLeave()
		}

		// Invalidate map size after layout change
		setTimeout(() => map.invalidateSize(), 50)
	}

	navTabs.forEach((tab) => {
		tab.addEventListener('click', () => switchTo(tab.dataset.view))
	})

	// CTA buttons in about view
	document.querySelectorAll('.about-cta[data-goto]').forEach((btn) => {
		btn.addEventListener('click', () => {
			const destination = btn.dataset.goto
			switchTo(destination)
			if (destination === 'explore' && onExplorePreset) {
				const preset = btn.dataset.explore
				if (preset) onExplorePreset(preset)
			}
		})
	})

	// Set initial state for about view
	content.classList.add('panel-full')
}
