#!/bin/bash
# start-tunnel.sh — Start Cloudflare Quick Tunnel for the Dragon's Den API server
#
# Usage: bash start-tunnel.sh
# 
# This starts the API server on port 5000 and creates a Cloudflare Quick Tunnel.
# The tunnel URL is saved to config.json and pushed to the repo.
# The web pages read config.json to find the API endpoint.
#
# To stop: kill the background processes (pkill -f "api-server.py" && pkill -f "cloudflared")

set -e

REPO_DIR="/Users/cerebral/dragons-den-board"
API_PORT=5000
CONFIG_FILE="$REPO_DIR/config.json"
LOG_FILE="/tmp/dragons-den-tunnel.log"

echo "🐉 Starting Dragon's Den tunnel..."

# Kill any existing processes
lsof -ti :$API_PORT | xargs kill -9 2>/dev/null || true
pkill -f "cloudflared.*$API_PORT" 2>/dev/null || true
sleep 1

# Start the API server in background
cd "$REPO_DIR"
nohup python3 api-server.py > /tmp/dragons-den-api.log 2>&1 &
echo "API server started (PID: $!)"

# Wait for API server
for i in $(seq 1 15); do
  if curl -s http://localhost:$API_PORT/api/data > /dev/null 2>&1; then
    echo "API server ready on port $API_PORT"
    break
  fi
  sleep 1
done

# Start cloudflared quick tunnel, logging to file
echo "Starting Cloudflare Quick Tunnel..."
nohup cloudflared tunnel --url http://localhost:$API_PORT > "$LOG_FILE" 2>&1 &
echo "Tunnel starting (PID: $!)"

# Wait for tunnel URL in log
echo "Waiting for tunnel URL..."
TUNNEL_URL=""
for i in $(seq 1 30); do
  if [ -f "$LOG_FILE" ]; then
    TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' "$LOG_FILE" | head -1)
    if [ -n "$TUNNEL_URL" ]; then
      break
    fi
  fi
  sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
  echo "ERROR: Could not get tunnel URL. Check $LOG_FILE"
  cat "$LOG_FILE"
  exit 1
fi

echo "✅ Tunnel URL: $TUNNEL_URL"

# Save to config.json
cat > "$CONFIG_FILE" << EOF
{"api_url": "$TUNNEL_URL", "updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF
echo "Saved to config.json"

# Push to repo
cd "$REPO_DIR"
git add config.json
git commit -m "Update tunnel URL: $TUNNEL_URL" 2>/dev/null || true
git push 2>/dev/null || true
echo "Pushed to GitHub"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐉 Dragon's Den is live!"
echo "   Web:  https://ringoaigit.github.io/dragons-den-board/"
echo "   API:  $TUNNEL_URL"
echo "   Pass: dragons"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The tunnel will stay active until you stop it."
echo "To restart after Mac reboot, run: bash $REPO_DIR/start-tunnel.sh"