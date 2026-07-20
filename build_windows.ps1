$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

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

$buildPython = Join-Path $PSScriptRoot ".build-venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $buildPython)) {
    Invoke-Checked { py -3 -m venv .build-venv } "Creating the build environment"
}

$buildPip = Join-Path $PSScriptRoot ".build-venv\Scripts\pip.exe"
if (-not (Test-Path -LiteralPath $buildPip)) {
    Invoke-Checked { py -3 -m venv --clear .build-venv } "Repairing the build environment"
}

Invoke-Checked { & $buildPython -m pip install --upgrade pip } "Upgrading pip"
Invoke-Checked { & $buildPython -m pip install -r requirements-build.txt } "Installing build dependencies"
Invoke-Checked { & $buildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "PDF Suite" `
    --icon app_icon.ico `
    --add-data "app_icon.ico;." `
    --collect-all customtkinter `
    app.pyw } "Building PDF Suite"

Write-Host "Build complete: dist\PDF Suite\PDF Suite.exe"
