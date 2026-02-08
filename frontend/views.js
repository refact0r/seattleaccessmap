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
		navTabs.forEach((t) => t.classList.remove('active'))
		document
			.querySelector(`.nav-tab[data-view="${viewId}"]`)
			?.classList.add('active')

		viewContents.forEach((v) => v.classList.remove('active'))
		document.getElementById('view-' + viewId)?.classList.add('active')

		content.classList.toggle(
			'panel-full',
			viewId === 'about' || viewId === 'analytics'
		)

		if (viewId === 'analytics') {
			onAnalyticsOpen()
		}
		if (viewId !== 'route' && onRouteLeave) {
			onRouteLeave()
		}

		setTimeout(() => map.invalidateSize(), 50)
	}

	navTabs.forEach((tab) => {
		tab.addEventListener('click', () => switchTo(tab.dataset.view))
	})

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

	content.classList.add('panel-full')
}
