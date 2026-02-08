const rootStyle = getComputedStyle(document.documentElement)

export const cssVar = (name, fallback = '') => {
	const value = rootStyle.getPropertyValue(name).trim()
	return value || fallback
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
		const h = ((parseFloat(nums[0]) || 0) % 360 + 360) % 360
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
	try {
		const probe = document.createElement('span')
		probe.style.color = trimmed
		document.body.appendChild(probe)
		const resolved = getComputedStyle(probe).color
		document.body.removeChild(probe)
		if (resolved && resolved.startsWith('rgb')) {
			const nums = resolved.match(/\d+/g) || []
			return nums.slice(0, 3).map((n) => parseInt(n, 10))
		}
	} catch (err) {
		console.warn('Color parse fallback failed', err)
	}
	return [0, 0, 0]
}

export const themeColors = {
	routeAccessible: cssVar('--route-accessible'),
	routeStandard: cssVar('--route-standard'),
	heatmapGradient: {
		0.2: cssVar('--severity-0'),
		0.4: cssVar('--severity-3'),
		0.6: cssVar('--severity-5'),
		0.8: cssVar('--severity-7'),
		1.0: cssVar('--severity-10'),
	},
	chartPalette: [
		cssVar('--chart-1'),
		cssVar('--chart-2'),
		cssVar('--chart-3'),
		cssVar('--chart-4'),
		cssVar('--chart-5'),
	],
}

const severityStops = [
	[0, parseColorToRgb(cssVar('--severity-0'))],
	[3, parseColorToRgb(cssVar('--severity-3'))],
	[5, parseColorToRgb(cssVar('--severity-5'))],
	[7, parseColorToRgb(cssVar('--severity-7'))],
	[10, parseColorToRgb(cssVar('--severity-10'))],
]

export function severityColor(val) {
	const v = Math.max(0, Math.min(10, val))
	for (let i = 0; i < severityStops.length - 1; i++) {
		const [lo, cLo] = severityStops[i]
		const [hi, cHi] = severityStops[i + 1]
		if (v <= hi) {
			const t = (v - lo) / (hi - lo)
			const r = Math.round(cLo[0] + t * (cHi[0] - cLo[0]))
			const g = Math.round(cLo[1] + t * (cHi[1] - cLo[1]))
			const b = Math.round(cLo[2] + t * (cHi[2] - cLo[2]))
			return `rgb(${r},${g},${b})`
		}
	}
	return `rgb(${severityStops[severityStops.length - 1][1].join(',')})`
}
