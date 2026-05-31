#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/web"

if [[ ! -d node_modules ]] || ! node -e "require('./node_modules/vite/package.json'); process.exit(Number(require('./node_modules/vite/package.json').version.split('.')[0]) >= 8 ? 1 : 0)" 2>/dev/null; then
  echo "Installing frontend dependencies (Vite 5 for Node 18)..."
  npm install
fi

echo "Building frontend..."
npm run build

cd "$ROOT"
echo ""
echo "Starting server at http://127.0.0.1:8000"
echo "Open that URL in your browser (not plain http://localhost — use port 8000)."
exec uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
