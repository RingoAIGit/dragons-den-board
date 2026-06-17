# 🐉 Dragon's Den

Opportunity review board for Neil's venture pipeline.

## Pages
- **Review** (`index.html`) — Full card details with decision buttons
- **Kanban** (`kanban.html`) — Board view grouped by stage

## How it works
- `data.json` — Source of truth (synced from `~/.hermes/data/opportunities.json`)
- `api-server.py` — Local server for decision button writes (port 5000)
- Cron jobs update `data.json` and push to this repo

## Setup
1. Run `python3 api-server.py` to start the local API server
2. Open http://localhost:5000 in your browser
3. Use decision buttons to move cards between stages
