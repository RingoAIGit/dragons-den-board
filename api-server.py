#!/usr/bin/env python3
"""
api-server.py — Tiny local API for Dragon's Den decision buttons.
Serves static files from the repo and handles card updates.
Runs on http://localhost:5000
"""

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import subprocess
from datetime import datetime, timezone

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.expanduser("~/.hermes/data/opportunities.json")
PORT = 5000

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=REPO_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/api/data':
            # Return the current opportunities data
            try:
                with open(DATA_FILE) as f:
                    data = json.load(f)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/update':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                update = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return

            # Load current data
            try:
                with open(DATA_FILE) as f:
                    data = json.load(f)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return

            # Find and update the card
            cards = data.get('opportunities', [])
            card = next((c for c in cards if c.get('id') == update.get('id')), None)
            if not card:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Card not found"}).encode())
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
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return

            # Sync to repo data.json
            sync_to_repo(data)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging
        pass

def sync_to_repo(data):
    """Copy data.json to the repo and commit/push."""
    try:
        repo_data = os.path.join(REPO_DIR, 'data.json')
        with open(repo_data, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Git add, commit, push
        subprocess.run(['git', 'add', 'data.json'], cwd=REPO_DIR, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Update opportunities data'], cwd=REPO_DIR, capture_output=True)
        subprocess.run(['git', 'push'], cwd=REPO_DIR, capture_output=True)
    except Exception as e:
        print(f"Repo sync error: {e}", file=sys.stderr)

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