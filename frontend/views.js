export function initViewTabs({ map, onAnalyticsOpen, onRouteLeave }) {
	const navTabs = document.querySelectorAll('.nav-tab')
	const viewContents = document.querySelectorAll('.view-content')

	navTabs.forEach((tab) => {
		tab.addEventListener('click', () => {
			const viewId = tab.dataset.view

			// Update tab state
			navTabs.forEach((t) => t.classList.remove('active'))
			tab.classList.add('active')

			// Update panel content
			viewContents.forEach((v) => v.classList.remove('active'))
			document.getElementById('view-' + viewId).classList.add('active')

			// View-specific actions
			if (viewId === 'analytics') {
				onAnalyticsOpen()
			}
			if (viewId !== 'route' && onRouteLeave) {
				onRouteLeave()
			}

			// Invalidate map size after layout change
			setTimeout(() => map.invalidateSize(), 50)
		})
	})
}
