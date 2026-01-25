# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Anachron V2 is a time-travel survival text adventure game. This is a Python-only refactor of the original dual Node.js+Python architecture, designed to reduce hosting costs.

**Core concept**: Players travel through historical eras carrying three modern items, building fulfillment (Belonging, Legacy, Freedom) until they choose to stay in a time period permanently.

## Architecture

### Simplified Two-Layer System (V2)

```
Browser <--Socket.IO + REST--> Python/Flask <--> PostgreSQL
```

1. **React Frontend** (`frontend/`)
   - Renders game UI via Socket.IO messages from Python
   - Uses shadcn/ui components, TanStack Query, Wouter routing
   - Main routes: `/` (terminal/game), `/chronicle/nexus` (leaderboard view)
   - Built files deployed to `static/`

2. **Python Server** (`game/`)
   - `server.py`: Flask-SocketIO server handling everything:
     - Static file serving (React app)
     - REST API endpoints
     - Socket.IO for real-time game communication
   - `routes.py`: REST API endpoints (saves, leaderboard, history, AoA)
   - `db.py`: Database operations via psycopg2
   - `game_api.py`: GameSession class - main API for game actions
   - `game.py`: Core game loop, NarrativeEngine for AI generation
   - `game_state.py`: Central state coordination
   - `prompts.py`: All Claude API prompts for narrative generation
   - `eras.py`: Historical era definitions (13 eras)
   - `config.py`: Tunable parameters

## Build & Development Commands

```bash
# Install Python dependencies
pip install -r requirements.txt
# or
pip install -e .

# Build frontend (from frontend/ directory)
cd frontend && npm install && npm run build
# Copy built files to static/
cp -r dist/* ../static/

# Run the server
cd game && python server.py

# Run with specific port
PORT=5000 python game/server.py
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (required)
- `ANTHROPIC_API_KEY`: Enables AI narrative generation (optional - falls back to demo mode)
- `PORT`: Server port (default: 5000)
- `SESSION_SECRET`: Flask session secret (auto-generated if not set)
- `DEBUG_MODE=true` + `DEBUG_ERA=era_id`: Force specific era for testing

## Key Socket Events

Frontend emits: `init`, `new_game`, `set_name`, `choose`, `save`, `load`, `resume`, `leaderboard`, `restart`

Python server emits messages with types: `ready`, `title`, `narrative`, `choices`, `state`, `game_over`, `error`

## REST API Endpoints

All endpoints prefixed with `/api`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /saves | Save game |
| GET | /saves/:userId/:gameId | Load game |
| DELETE | /saves/:userId/:gameId | Delete game |
| GET | /saves/:userId | List user's games |
| POST | /leaderboard | Add score |
| GET | /leaderboard | Get top scores |
| GET | /leaderboard/:userId | Get user's scores |
| POST | /history | Save game history |
| GET | /history/:gameId | Get game history |
| GET | /histories/:userId | Get user's histories |
| POST | /aoa | Save AoA entry |
| GET | /aoa/entry/:entryId | Get AoA entry |
| GET | /aoa/user/:userId | Get user's AoA entries |
| GET | /aoa/recent | Get recent AoA entries |
| GET | /aoa/count | Count AoA entries |

## Database

- PostgreSQL with psycopg2
- Tables: game_saves, leaderboard_entries, game_histories, aoa_entries
- Same schema as V1 (compatible with existing data)

## Deployment (Railway)

1. Push to GitHub
2. Connect Railway to repo
3. Set environment variables (DATABASE_URL, ANTHROPIC_API_KEY)
4. Railway auto-detects Python and uses Procfile

## Python Game Modules

| Module | Purpose |
|--------|---------|
| `config.py` | All tunable parameters |
| `time_machine.py` | Window mechanics, era transitions |
| `fulfillment.py` | Hidden anchor tracking |
| `items.py` | Modern item inventory |
| `eras.py` | Era definitions with historical context |
| `prompts.py` | System prompts for Claude API |
| `scoring.py` | Score calculation and leaderboard logic |

## Changes from V1

- Removed Node.js/Express layer entirely
- Python now serves static files directly
- REST API ported from TypeScript to Python
- Database operations use psycopg2 instead of Drizzle ORM
- Single process instead of Node.js spawning Python
