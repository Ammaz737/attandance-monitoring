$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
& backend/.venv/Scripts/python.exe -m pytest backend/tests -q
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
npm.cmd --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
