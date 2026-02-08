import { API_BASE_URL } from './config.js'

export function showBackendError() {
	if (document.getElementById('backend-error')) return
	const div = document.createElement('div')
	div.id = 'backend-error'
	div.className = 'backend-error'
	div.innerHTML = `
		<h3 class="backend-error-title">Cannot Connect to Backend</h3>
		<p class="backend-error-text">Start the backend server:</p>
		<pre class="backend-error-command">python3 backend/app.py</pre>
		<p class="backend-error-hint">Server should be on <strong>${API_BASE_URL}</strong></p>`
	document.body.appendChild(div)
}
