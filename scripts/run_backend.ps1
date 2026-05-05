$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$backendDir = Join-Path $repoRoot "backend"

Write-Host "[UrbanFix] Starting backend demo runner..." -ForegroundColor Cyan

# Activate virtual environment if present
$venvCandidates = @(
    (Join-Path $repoRoot "venv\Scripts\Activate.ps1"),
    (Join-Path $backendDir "venv\Scripts\Activate.ps1")
)

$activated = $false
foreach ($venv in $venvCandidates) {
    if (Test-Path $venv) {
        Write-Host "[UrbanFix] Activating venv: $venv" -ForegroundColor Yellow
        & $venv
        $activated = $true
        break
    }
}

if (-not $activated) {
    Write-Host "[UrbanFix] No venv found. Using current Python environment." -ForegroundColor Yellow
}

Set-Location $backendDir

Write-Host "[UrbanFix] Running migrations (alembic upgrade head)..." -ForegroundColor Cyan
alembic upgrade head

Write-Host "[UrbanFix] Launching API on http://localhost:8000" -ForegroundColor Green
uvicorn app.main:app --reload --port 8000
