Param(
    [switch]$SkipInstall
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $projectRoot

if (-Not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created default .env (edit it before running in production)." -ForegroundColor Yellow
}

if (-Not (Test-Path ".venv")) {
    python -m venv .venv
}

& ".\.venv\Scripts\Activate.ps1"

if (-Not $SkipInstall) {
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
}

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

