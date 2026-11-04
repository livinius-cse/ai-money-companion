# Start the FastAPI backend server
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$apiDir = Join-Path $rootDir "apps\api"

Write-Host "Starting AI Money Companion FastAPI backend..." -ForegroundColor Cyan
Set-Location $apiDir
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
