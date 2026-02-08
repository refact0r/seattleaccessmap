export function initAnalytics({ severityColor, cssVar, themeColors }) {
	let analyticsLoaded = false

	const chartColors = themeColors.chartPalette.slice().reverse()
	const paletteFor = (count) => {
		if (count <= chartColors.length) {
			return chartColors.slice(0, count)
		}
		const expanded = chartColors.slice()
		while (expanded.length < count) {
			expanded.push(chartColors[chartColors.length - 1])
		}
		return expanded
	}

	function renderCharts(data) {
		const defaultOpts = {
			responsive: true,
			maintainAspectRatio: true,
			plugins: {
				legend: { display: false },
			},
		}

		new Chart(document.getElementById('chart-type-count'), {
			type: 'bar',
			data: {
				labels: data.type_counts.labels,
				datasets: [
					{
						data: data.type_counts.values,
						backgroundColor: paletteFor(
							data.type_counts.labels.length,
						),
						borderRadius: 4,
					},
				],
			},
			options: {
				...defaultOpts,
				indexAxis: 'y',
				scales: {
					x: { grid: { display: false } },
					y: { grid: { display: false } },
				},
			},
		})

		new Chart(document.getElementById('chart-type-severity'), {
			type: 'bar',
			data: {
				labels: data.type_severity.labels,
				datasets: [
					{
						data: data.type_severity.values,
						backgroundColor: paletteFor(
							data.type_severity.labels.length,
						),
						borderRadius: 4,
					},
				],
			},
			options: {
				...defaultOpts,
				indexAxis: 'y',
				scales: {
					x: { grid: { display: false }, max: 5 },
					y: { grid: { display: false } },
				},
			},
		})

		new Chart(document.getElementById('chart-top-neighborhoods'), {
			type: 'bar',
			data: {
				labels: data.top_neighborhoods.labels,
				datasets: [
					{
						data: data.top_neighborhoods.values,
						backgroundColor: cssVar('--chart-4'),
						borderRadius: 4,
					},
				],
			},
			options: {
				...defaultOpts,
				indexAxis: 'y',
				scales: {
					x: { grid: { display: false } },
					y: { grid: { display: false } },
				},
			},
		})

		new Chart(document.getElementById('chart-bottom-neighborhoods'), {
			type: 'bar',
			data: {
				labels: data.bottom_neighborhoods.labels,
				datasets: [
					{
						data: data.bottom_neighborhoods.values,
						backgroundColor: cssVar('--chart-1'),
						borderRadius: 4,
					},
				],
			},
			options: {
				...defaultOpts,
				indexAxis: 'y',
				scales: {
					x: { grid: { display: false } },
					y: { grid: { display: false } },
				},
			},
		})

		new Chart(document.getElementById('chart-severity-dist'), {
			type: 'bar',
			data: {
				labels: data.severity_distribution.labels,
				datasets: [
					{
						data: data.severity_distribution.values,
						backgroundColor: cssVar('--chart-5'),
						borderRadius: 2,
					},
				],
			},
			options: {
				...defaultOpts,
				scales: {
					x: {
						grid: { display: false },
						title: {
							display: true,
							text: 'Adjusted Severity',
						},
					},
					y: {
						grid: { display: false },
						title: { display: true, text: 'Count' },
					},
				},
			},
		})

		renderSeverityHeatmapTable(data.neighborhood_type_severity)
	}

	function renderSeverityHeatmapTable(data) {
		const table = document.getElementById('severity-heatmap-table')
		const { neighborhoods, types, matrix } = data

		let html = '<thead><tr><th></th>'
		types.forEach((t) => {
			html += `<th>${t.replace('Problem', 'Prob.').replace('Sidewalk', 'SW')}</th>`
		})
		html += '</tr></thead><tbody>'

		neighborhoods.forEach((n, i) => {
			html += `<tr><td title="${n}">${n}</td>`
			types.forEach((_, j) => {
				const val = matrix[i][j]
				if (val === null) {
					html +=
						'<td class="severity-cell severity-cell--empty">-</td>'
				} else {
					const color = severityColor(val)
					html += `<td class="severity-cell" style="background:${color};" title="${n}: ${val.toFixed(1)}">${val.toFixed(1)}</td>`
				}
			})
			html += '</tr>'
		})

		html += '</tbody>'
		table.innerHTML = html
	}

	async function loadAnalytics() {
		const container = document.getElementById('analytics-container')

		try {
			const response = await fetch('http://localhost:5001/api/analytics')
			if (!response.ok) throw new Error('Failed to load analytics')
			const data = await response.json()

			analyticsLoaded = true

			container.innerHTML = `
				<div class="chart-grid">
					<div class="chart-card">
						<h4>Barrier Count by Type</h4>
						<canvas id="chart-type-count"></canvas>
						<p class="chart-caption">CurbRamp observations dominate the dataset since they mark existing ramps at every corner. NoSidewalk and Obstacle reports are rarer.</p>
					</div>
					<div class="chart-card">
						<h4>Mean Raw Severity by Type (1-5)</h4>
						<canvas id="chart-type-severity"></canvas>
						<p class="chart-caption">Raw severity (1-5) as labeled by Project Sidewalk. NoSidewalk and NoCurbRamp tend to score highest. Note that these values don't account for differences between barrier types. See the adjusted severity metric on the About page.</p>
					</div>
					<div class="chart-card chart-card--wide">
						<h4>Adjusted Severity Distribution</h4>
						<canvas id="chart-severity-dist"></canvas>
						<p class="chart-caption">Most barriers fall in the low-to-moderate severity range. The peak at the low end is mostly driven by CurbRamp observations, which represent existing ramps.</p>
					</div>
					<div class="chart-card">
						<h4>Top 10 Neighborhoods by Barrier Count</h4>
						<canvas id="chart-top-neighborhoods"></canvas>
						<p class="chart-caption">High barrier counts likely reflect poor accessibility in these neighborhoods.</p>
					</div>
					<div class="chart-card">
						<h4>Bottom 10 Neighborhoods by Barrier Count</h4>
						<canvas id="chart-bottom-neighborhoods"></canvas>
						<p class="chart-caption">Low counts could indicate good sidewalk conditions or limited survey coverage.</p>
					</div>
					<div class="chart-card chart-card--wide">
						<h4>Neighborhood × Type Severity Heatmap</h4>
						<div class="table-scroll">
							<table class="severity-table" id="severity-heatmap-table"></table>
						</div>
						<p class="chart-caption">Mean adjusted severity by neighborhood and barrier type. Different neighborhoods have different severity profiles across barrier categories.</p>
					</div>
				</div>`

			renderCharts(data)
		} catch (err) {
			console.error('Error loading analytics:', err)
			container.innerHTML = `
				<div class="analytics-error">
					<p><strong>Failed to load analytics</strong></p>
					<p class="analytics-error-subtext">
						Make sure the backend is running with the /api/analytics endpoint.
					</p>
				</div>`
		}
	}

	return {
		loadAnalyticsIfNeeded: () => {
			if (!analyticsLoaded) loadAnalytics()
		},
	}
}
