export const API_BASE_URL =
	'https://uncondemnable-disorganizedly-nerissa.ngrok-free.dev'

export function apiFetch(path, options = {}) {
	const headers = {
		'ngrok-skip-browser-warning': 'true',
		...(options.headers || {}),
	}
	return fetch(`${API_BASE_URL}${path}`, { ...options, headers })
}
