import { dataFetch } from './config.js'

let nodes = null // { "osmid": [lat, lng] }
let adj = null // adjacency list: { nodeId: [[neighborId, length, accCost], ...] }
let edgeGeom = null // { "u,v": [[lat,lng], ...] }
let nodeIds = null // array of node id strings for nearest-node scan
let nodeLats = null // Float64Array for fast scanning
let nodeLngs = null // Float64Array for fast scanning
let cosLat = 1 // cos(mean latitude) for distance correction

// Binary min-heap for Dijkstra
class MinHeap {
	constructor() {
		this.data = []
	}

	push(priority, value) {
		this.data.push([priority, value])
		this._bubbleUp(this.data.length - 1)
	}

	pop() {
		const top = this.data[0]
		const last = this.data.pop()
		if (this.data.length > 0) {
			this.data[0] = last
			this._sinkDown(0)
		}
		return top
	}

	get size() {
		return this.data.length
	}

	_bubbleUp(i) {
		const d = this.data
		while (i > 0) {
			const parent = (i - 1) >> 1
			if (d[i][0] >= d[parent][0]) break
			;[d[i], d[parent]] = [d[parent], d[i]]
			i = parent
		}
	}

	_sinkDown(i) {
		const d = this.data
		const n = d.length
		while (true) {
			let smallest = i
			const left = 2 * i + 1
			const right = 2 * i + 2
			if (left < n && d[left][0] < d[smallest][0]) smallest = left
			if (right < n && d[right][0] < d[smallest][0]) smallest = right
			if (smallest === i) break
			;[d[i], d[smallest]] = [d[smallest], d[i]]
			i = smallest
		}
	}
}

export async function loadGraph() {
	const response = await dataFetch('graph.json')
	const data = await response.json()

	nodes = data.nodes
	edgeGeom = data.geom || {}

	// Build adjacency list and arrays for nearest-node scanning
	nodeIds = Object.keys(nodes)
	const n = nodeIds.length
	nodeLats = new Float64Array(n)
	nodeLngs = new Float64Array(n)

	let latSum = 0
	for (let i = 0; i < n; i++) {
		const coords = nodes[nodeIds[i]]
		nodeLats[i] = coords[0]
		nodeLngs[i] = coords[1]
		latSum += coords[0]
	}
	cosLat = Math.cos((latSum / n) * (Math.PI / 180))

	// Build adjacency list from edges
	// edges: [[u, v, length, acc_cost], ...]
	// Graph already has separate (u,v) and (v,u) edges — no need to add reverse
	adj = {}
	for (let i = 0; i < n; i++) {
		adj[nodeIds[i]] = []
	}

	for (const edge of data.edges) {
		const [u, v, length, accCost] = edge
		const uStr = String(u)
		if (adj[uStr]) adj[uStr].push([String(v), length, accCost])
	}
}

function findNearestNode(lat, lng) {
	const lngCorrected = lng * cosLat
	let bestDist = Infinity
	let bestIdx = 0

	for (let i = 0; i < nodeIds.length; i++) {
		const dLat = nodeLats[i] - lat
		const dLng = nodeLngs[i] * cosLat - lngCorrected
		const dist = dLat * dLat + dLng * dLng
		if (dist < bestDist) {
			bestDist = dist
			bestIdx = i
		}
	}

	return nodeIds[bestIdx]
}

function dijkstra(startNode, endNode, barrierWeight) {
	const dist = {}
	const prev = {}
	const heap = new MinHeap()

	dist[startNode] = 0
	heap.push(0, startNode)

	while (heap.size > 0) {
		const [d, u] = heap.pop()
		if (u === endNode) break
		if (d > (dist[u] ?? Infinity)) continue

		const neighbors = adj[u]
		if (!neighbors) continue

		for (const [v, length, accCost] of neighbors) {
			let w
			if (barrierWeight < 0.01) {
				w = length
			} else {
				w = length + barrierWeight * Math.pow(accCost, 1.5)
			}

			const newDist = d + w
			if (newDist < (dist[v] ?? Infinity)) {
				dist[v] = newDist
				prev[v] = u
				heap.push(newDist, v)
			}
		}
	}

	if (!(endNode in prev) && startNode !== endNode) {
		return null
	}

	// Reconstruct path
	const path = []
	let current = endNode
	while (current !== undefined) {
		path.push(current)
		current = prev[current]
	}
	path.reverse()
	return path
}

function pathToGeoJSON(path) {
	if (!path || path.length < 2) return null

	const coordinates = []

	for (let i = 0; i < path.length - 1; i++) {
		const u = path[i]
		const v = path[i + 1]

		// Check for stored geometry (curved edges)
		const geomKey = `${u},${v}`
		const geomKeyReverse = `${v},${u}`

		if (edgeGeom[geomKey]) {
			const coords = edgeGeom[geomKey]
			for (let j = i === 0 ? 0 : 1; j < coords.length; j++) {
				coordinates.push([coords[j][1], coords[j][0]]) // [lng, lat]
			}
		} else if (edgeGeom[geomKeyReverse]) {
			const coords = edgeGeom[geomKeyReverse]
			for (let j = coords.length - (i === 0 ? 1 : 2); j >= 0; j--) {
				coordinates.push([coords[j][1], coords[j][0]]) // [lng, lat]
			}
		} else {
			// Straight line between nodes
			if (i === 0) {
				const uCoords = nodes[u]
				coordinates.push([uCoords[1], uCoords[0]])
			}
			const vCoords = nodes[v]
			coordinates.push([vCoords[1], vCoords[0]])
		}
	}

	return {
		type: 'FeatureCollection',
		features: [
			{
				type: 'Feature',
				geometry: {
					type: 'LineString',
					coordinates,
				},
				properties: {},
			},
		],
	}
}

function computeRouteStats(path, barrierWeight) {
	let totalLength = 0
	let totalBarrierCost = 0
	let totalBarrierCount = 0

	for (let i = 0; i < path.length - 1; i++) {
		const u = path[i]
		const v = path[i + 1]

		// Find the best edge in adjacency list
		const neighbors = adj[u]
		let bestWeight = Infinity
		let bestLength = 0
		let bestAccCost = 0

		for (const [neighbor, length, accCost] of neighbors) {
			if (neighbor === v) {
				const w =
					barrierWeight < 0.01
						? length
						: length + barrierWeight * Math.pow(accCost, 1.5)
				if (w < bestWeight) {
					bestWeight = w
					bestLength = length
					bestAccCost = accCost
				}
			}
		}

		totalLength += bestLength
		totalBarrierCost += bestAccCost
		if (bestAccCost > 0) totalBarrierCount++
	}

	return {
		length: totalLength,
		barrier_cost: totalBarrierCost,
		barrier_count: totalBarrierCount,
	}
}

export function calculateRoute(
	startLat,
	startLng,
	endLat,
	endLng,
	barrierWeight,
) {
	if (!nodes || !adj) {
		throw new Error('Graph not loaded. Call loadGraph() first.')
	}

	const startNode = findNearestNode(startLat, startLng)
	const endNode = findNearestNode(endLat, endLng)

	const startCoords = nodes[startNode]
	const endCoords = nodes[endNode]

	// Calculate accessible route (with barrier weight)
	const accessiblePath = dijkstra(startNode, endNode, barrierWeight)
	if (!accessiblePath) {
		throw new Error('No path found between the specified points')
	}

	// Calculate standard route (shortest distance only)
	const standardPath = dijkstra(startNode, endNode, 0)
	if (!standardPath) {
		throw new Error('No path found between the specified points')
	}

	const accessibleGeoJSON = pathToGeoJSON(accessiblePath)
	const standardGeoJSON = pathToGeoJSON(standardPath)

	const accessibleStats = computeRouteStats(accessiblePath, barrierWeight)
	const standardStats = computeRouteStats(standardPath, 0)

	return {
		accessible_route: accessibleGeoJSON,
		standard_route: standardGeoJSON,
		stats: {
			accessible_length: accessibleStats.length,
			accessible_barrier_cost: accessibleStats.barrier_cost,
			accessible_barrier_count: accessibleStats.barrier_count,
			standard_length: standardStats.length,
			standard_barrier_cost: standardStats.barrier_cost,
			standard_barrier_count: standardStats.barrier_count,
		},
		snapped_start: { lat: startCoords[0], lng: startCoords[1] },
		snapped_end: { lat: endCoords[0], lng: endCoords[1] },
	}
}
