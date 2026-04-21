# CompressorIQ — start API + Next.js dev servers in separate windows.
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File ".\start-dev.ps1"
# Or double-click:     start-dev.cmd

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Backend venv not found. Creating and installing deps (one-time)..." -ForegroundColor Yellow
    Push-Location $Backend
    try {
        python -m venv .venv
        & $Python -m pip install -r requirements.txt
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies (one-time)..." -ForegroundColor Yellow
    Push-Location $Frontend
    try {
        npm install
    }
    finally {
        Pop-Location
    }
}

$backendCmd = @"
Set-Location -LiteralPath "$Backend"
& "$Python" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
"@

$frontendCmd = @"
Set-Location -LiteralPath "$Frontend"
npm run dev
"@

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoLogo",
    "-Command",
    $backendCmd
) -WindowStyle Normal

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoLogo",
    "-Command",
    $frontendCmd
) -WindowStyle Normal

Write-Host ""
Write-Host "Started two windows:" -ForegroundColor Green
Write-Host "  API:  http://127.0.0.1:8001  (docs: /docs)"
Write-Host "  App:  http://localhost:3000  (Next may use 3001 if 3000 is busy)"
Write-Host ""
Write-Host "Close each window or press Ctrl+C in it to stop that server."
Write-Host ""
