const meta = document.querySelector('meta[name="api-base-url"]')

export const API_BASE_URL =
	(window.API_BASE_URL && String(window.API_BASE_URL)) ||
	(meta && meta.content) ||
	'http://localhost:5001'
