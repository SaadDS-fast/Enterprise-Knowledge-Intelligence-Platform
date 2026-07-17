#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e "./backend[dev]"
(cd frontend && npm ci)
echo "Bootstrap complete. Run 'make backend' and 'make frontend', or 'docker compose up --build'."
