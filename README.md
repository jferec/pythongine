# pythongine

Small chess engine with a web analysis UI.

## Tests

```bash
uv run pytest
```

## Analysis UI

### Quick start (single URL)

Builds the frontend and serves UI + API together on **http://127.0.0.1:8000**:

```bash
chmod +x scripts/serve_ui.sh
./scripts/serve_ui.sh
```

Or manually:

```bash
cd web && npm install && npm run build && cd ..
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000** in your browser. Plain `http://localhost` (port 80) will show nothing — you must use port **8000** (or **5173** in dev mode below).

Requires **Node 18+** (Vite 5; Node 20+ optional).

### Development (hot reload)

Terminal 1 — API:

```bash
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — Vite dev server (proxies `/api` → port 8000):

```bash
cd web && npm install && npm run dev
```

Open **http://localhost:5173**

Paste a Lichess game URL or 8-character game id to load and analyze positions (5-minute timeout per ply).

Alternative API entry:

```bash
uv run python main.py serve
```
