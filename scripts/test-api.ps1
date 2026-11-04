# Run backend test suite
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$apiDir = Join-Path $rootDir "apps\api"

Write-Host "Running backend Pytest test suite..." -ForegroundColor Cyan
Set-Location $apiDir
& ".\.venv\Scripts\python.exe" -m pytest tests -v
