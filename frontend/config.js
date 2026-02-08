const DATA_BASE = './data'

export function dataFetch(path) {
	return fetch(`${DATA_BASE}/${path}`)
}
