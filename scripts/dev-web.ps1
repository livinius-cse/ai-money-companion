# Start the Next.js frontend dev server
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$webDir = Join-Path $rootDir "apps\web"

Write-Host "Starting AI Money Companion Next.js web application..." -ForegroundColor Cyan
Set-Location $webDir
& "pnpm.cmd" run dev
