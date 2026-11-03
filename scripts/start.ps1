param([ValidateSet('backend','frontend')][string]$Service = 'backend')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if ($Service -eq 'backend') {
    $pythonPath = Join-Path $projectRoot 'backend/.venv/Scripts/python.exe'
    if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Run scripts/setup.ps1 first.' }
    & $pythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
} else {
    npm.cmd --prefix frontend run dev
}
