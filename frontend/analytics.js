export function initAnalytics({ severityColor, cssVar, themeColors }) {
	let analyticsLoaded = false

	const chartColors = themeColors.chartPalette
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
						backgroundColor: paletteFor(data.type_counts.labels.length),
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
						backgroundColor: paletteFor(data.type_severity.labels.length),
						borderRadius: 4,
					},
				],
			},
			options: {
				...defaultOpts,
				indexAxis: 'y',
				scales: {
					x: { grid: { display: false }, max: 10 },
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

		new Chart(document.getElementById('chart-bottom-neighborhoods'), {
			type: 'bar',
			data: {
				labels: data.bottom_neighborhoods.labels,
				datasets: [
					{
						data: data.bottom_neighborhoods.values,
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
					html += '<td class="severity-cell severity-cell--empty">-</td>'
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
				<div class="chart-card">
					<h4>Barrier Count by Type</h4>
					<canvas id="chart-type-count"></canvas>
				</div>
				<div class="chart-card">
					<h4>Mean Severity by Type</h4>
					<canvas id="chart-type-severity"></canvas>
				</div>
				<div class="chart-card">
					<h4>Top 10 Neighborhoods by Barrier Count</h4>
					<canvas id="chart-top-neighborhoods"></canvas>
				</div>
				<div class="chart-card">
					<h4>Bottom 10 Neighborhoods by Barrier Count</h4>
					<canvas id="chart-bottom-neighborhoods"></canvas>
				</div>
				<div class="chart-card">
					<h4>Severity Distribution</h4>
					<canvas id="chart-severity-dist"></canvas>
				</div>
				<div class="chart-card">
					<h4>Neighborhood × Type Severity</h4>
					<div class="table-scroll">
						<table class="severity-table" id="severity-heatmap-table"></table>
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
