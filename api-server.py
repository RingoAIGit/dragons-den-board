#!/usr/bin/env python3
"""
api-server.py — Tiny local API for Dragon's Den decision buttons.
Serves static files from the repo and handles card updates.
Runs on http://localhost:5000
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import subprocess
from datetime import datetime, timezone

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.expanduser("~/.hermes/data/opportunities.json")
PORT = 5000

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        
        if path == '/api/data':
            self._send_json(self._load_data())
            return
        
        # Serve static files
        self._serve_static()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        
        if path == '/api/update':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                update = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            # Load current data
            data = self._load_data()
            if isinstance(data, dict) and 'error' in data:
                self._send_json(data, 500)
                return

            # Find and update the card
            cards = data.get('opportunities', [])
            card = next((c for c in cards if c.get('id') == update.get('id')), None)
            if not card:
                self._send_json({"error": "Card not found"}, 404)
                return

            # Apply updates
            if 'status' in update:
                card['status'] = update['status']
            if 'reviewed' in update:
                card['reviewed'] = update['reviewed']
            if 'drop_reason' in update:
                card['drop_reason'] = update['drop_reason']
            if 'next_action' in update:
                card['next_action'] = update['next_action']
            card['last_updated'] = datetime.now(timezone.utc).isoformat()

            # Save back
            try:
                with open(DATA_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
                return

            # Sync to repo data.json
            self._sync_to_repo(data)

            self._send_json({"ok": True})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _load_data(self):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception as e:
            return {"error": str(e)}

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self._cors_headers()
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _serve_static(self):
        # Map URL path to file
        path = urlparse(self.path).path
        if path == '/':
            path = '/index.html'
        filepath = os.path.join(REPO_DIR, path.lstrip('/'))
        
        if os.path.isfile(filepath):
            ext = os.path.splitext(filepath)[1]
            mime = {'.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json'}.get(ext, 'application/octet-stream')
            with open(filepath, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._send_json({"error": "Not found"}, 404)

    def _sync_to_repo(self, data):
        """Copy data.json to the repo and commit/push."""
        try:
            repo_data = os.path.join(REPO_DIR, 'data.json')
            with open(repo_data, 'w') as f:
                json.dump(data, f, indent=2)
            subprocess.run(['git', 'add', 'data.json'], cwd=REPO_DIR, capture_output=True)
            result = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=REPO_DIR)
            if result.returncode != 0:
                subprocess.run(['git', 'commit', '-m', f'Update {datetime.now().strftime("%Y-%m-%d %H:%M")}'], cwd=REPO_DIR, capture_output=True)
                subprocess.run(['git', 'push'], cwd=REPO_DIR, capture_output=True)
        except Exception as e:
            print(f"Repo sync error: {e}", file=sys.stderr)

    def log_message(self, format, *args):
        pass  # Suppress default logging

if __name__ == '__main__':
    print(f"🐉 Dragon's Den API server running on http://localhost:{PORT}")
    print(f"   Data file: {DATA_FILE}")
    print(f"   Repo dir:  {REPO_DIR}")
    print(f"   Press Ctrl+C to stop")
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()