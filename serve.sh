#!/bin/bash
# Simple HTTP server for viewing the accessibility map
# This avoids CORS issues when loading JSON files locally

echo "Starting local server at http://localhost:8000"
echo "Open http://localhost:8000/index.html in your browser"
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m http.server 8000
