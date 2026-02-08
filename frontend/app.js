const API_URL = 'http://localhost:5000/api'

// Initialize map centered on Seattle
const map = L.map('map').setView([47.6062, -122.3321], 12)

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
	attribution: '&copy; OpenStreetMap contributors',
}).addTo(map)

// Check API health
fetch(`${API_URL}/health`)
	.then((r) => r.json())
	.then((data) => console.log('API Health:', data))
	.catch((err) => console.error('API not available:', err))
