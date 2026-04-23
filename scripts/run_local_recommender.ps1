$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host "[recommender-local] $msg" }

$repoRoot = Split-Path -Parent $PSScriptRoot
$svcDir = Join-Path $repoRoot "recommender-ai-service"

if (!(Test-Path $svcDir)) {
  throw "Cannot find recommender-ai-service at: $svcDir"
}

Set-Location $svcDir

Info "Using service dir: $svcDir"

# --- DB: use SQLite for local dev (no Postgres needed) ---
$env:DB_ENGINE = "sqlite"

# --- Point recommender at Docker-exposed service ports ---
# These are published by docker-compose.override.yml
$env:ORDER_SERVICE_URL = "http://localhost:8001"
$env:PRODUCT_SERVICE_URL = "http://localhost:8002"
$env:COMMENT_RATE_SERVICE_URL = "http://localhost:8003"

# --- Optional toggles ---
# $env:BEHAVIOR_DL_ENABLED = "False"

if (Test-Path ".\\.venv\\Scripts\\Activate.ps1") {
  Info "Activating venv (.venv)"
  . .\\.venv\\Scripts\\Activate.ps1
} else {
  Info "No .venv found. If you haven't yet:"
  Info "  py -3.11 -m venv .venv"
  Info "  .\\.venv\\Scripts\\Activate.ps1"
  Info "  pip install -r requirements.txt"
}

Info "Running migrations (SQLite)"
python manage.py migrate

Info "Starting Django dev server on http://localhost:8006"
python manage.py runserver 0.0.0.0:8006

