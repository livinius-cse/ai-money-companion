# Export OpenAPI schema and compile TypeScript definitions
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$apiDir = Join-Path $rootDir "apps\api"
$webDir = Join-Path $rootDir "apps\web"

Write-Host "1. Exporting OpenAPI schema from FastAPI..." -ForegroundColor Cyan
Set-Location $apiDir
& ".\.venv\Scripts\python.exe" ".\scripts\dump_openapi.py"

Write-Host "2. Compiling TypeScript definitions..." -ForegroundColor Cyan
Set-Location $webDir
& "pnpm.cmd" exec openapi-typescript ".\src\types\openapi.json" -o ".\src\types\api.d.ts"

Write-Host "Type synchronization complete: apps/web/src/types/api.d.ts" -ForegroundColor Green
Set-Location $rootDir
