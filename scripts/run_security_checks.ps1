$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\backend")
ruff check app tests
bandit -q -r app -x tests
pip-audit
