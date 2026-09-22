[CmdletBinding()]
param(
    [switch]$SkipMigrations,
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$frontendRoot = Join-Path $repoRoot "frontend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required. Install Docker Desktop and try again."
}
if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found at $python. Run the backend install steps first."
}
if (-not (Test-Path (Join-Path $frontendRoot "node_modules"))) {
    throw "Frontend dependencies are missing. Run 'npm install' in frontend first."
}

Push-Location $repoRoot
try {
    Write-Host "Starting PostgreSQL only..." -ForegroundColor Cyan
    docker compose up -d db

    Write-Host "Waiting for PostgreSQL to become healthy..." -ForegroundColor Cyan
    $healthy = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $health = docker inspect --format "{{.State.Health.Status}}" meridian-db 2>$null
        if ($health -eq "healthy") {
            $healthy = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $healthy) {
        docker compose logs db
        throw "PostgreSQL did not become healthy."
    }

    # Environment variables override backend/.env, which may be configured for SQLite.
    $env:DATABASE_URL = "postgresql+psycopg://meridian:meridian@localhost:5432/meridian"
    $env:FRONTEND_URL = "http://localhost:5173"
    $env:BACKEND_URL = "http://localhost:8000"
    $env:SESSION_COOKIE_SECURE = "false"
    $env:DEV_LOGIN_ENABLED = "true"

    if (-not $SkipMigrations) {
        Write-Host "Applying database migrations..." -ForegroundColor Cyan
        Push-Location $backendRoot
        try {
            & $python -m alembic upgrade head
            if ($LASTEXITCODE -ne 0) {
                throw "Database migrations failed."
            }
        }
        finally {
            Pop-Location
        }
    }

    if (-not $SkipSeed) {
        Write-Host "Seeding sample data..." -ForegroundColor Cyan
        Push-Location $backendRoot
        try {
            & $python -m app.seed
            if ($LASTEXITCODE -ne 0) {
                throw "Database seed failed."
            }
        }
        finally {
            Pop-Location
        }
    }

    Write-Host "Starting backend at http://localhost:8000 ..." -ForegroundColor Green
    Start-Process -FilePath $python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000" `
        -WorkingDirectory $backendRoot

    Write-Host "Starting frontend at http://localhost:5173 ..." -ForegroundColor Green
    Start-Process -FilePath "npm.cmd" `
        -ArgumentList "run", "dev", "--", "--host", "0.0.0.0" `
        -WorkingDirectory $frontendRoot

    Write-Host ""
    Write-Host "Local development is running:" -ForegroundColor Green
    Write-Host "  PostgreSQL: localhost:5432 (Docker)"
    Write-Host "  Backend:    http://localhost:8000"
    Write-Host "  Frontend:   http://localhost:5173"
    Write-Host ""
    Write-Host "Stop the local backend/frontend windows separately. PostgreSQL remains available via:"
    Write-Host "  docker compose stop db"
}
finally {
    Pop-Location
}
