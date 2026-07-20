$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command,
        [Parameter(Mandatory = $true)]
        [string] $Description
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

$env:UV_PROJECT_ENVIRONMENT = Join-Path $projectRoot ".build-venv"
Invoke-Checked { uv sync --locked --group build } "Synchronizing build dependencies"

$buildPython = Join-Path $env:UV_PROJECT_ENVIRONMENT "Scripts\python.exe"
Invoke-Checked { & $buildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --specpath build `
    --windowed `
    --name "PDF Suite" `
    --icon assets\app_icon.ico `
    --add-data "assets\app_icon.ico;assets" `
    --collect-all customtkinter `
    app.pyw } "Building PDF Suite"

Write-Host "Build complete: dist\PDF Suite\PDF Suite.exe"
