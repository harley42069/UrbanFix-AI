$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$frontendDir = Join-Path $repoRoot "frontend"

Write-Host "[UrbanFix] Starting frontend demo runner..." -ForegroundColor Cyan
Set-Location $frontendDir

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "[UrbanFix] node_modules not found. Installing dependencies..." -ForegroundColor Yellow
    npm install
} else {
    Write-Host "[UrbanFix] node_modules found. Skipping npm install." -ForegroundColor Green
}

$envExample = Join-Path $frontendDir ".env.local.example"
$envLocal = Join-Path $frontendDir ".env.local"
if ((Test-Path $envExample) -and (-not (Test-Path $envLocal))) {
    Copy-Item $envExample $envLocal
    Write-Host "[UrbanFix] Created .env.local from .env.local.example" -ForegroundColor Green
} elseif (Test-Path $envLocal) {
    Write-Host "[UrbanFix] .env.local already exists." -ForegroundColor Green
} else {
    Write-Host "[UrbanFix] WARNING: .env.local.example not found." -ForegroundColor Yellow
}

Write-Host "[UrbanFix] Launching frontend on http://localhost:3000" -ForegroundColor Green
npm run dev
