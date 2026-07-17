#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
ruff check app tests
bandit -q -r app -x tests
pip-audit
