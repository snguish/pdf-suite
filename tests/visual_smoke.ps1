param(
    [Parameter(Mandatory = $true)] [string] $PdfPath,
    [string] $Executable = (Join-Path $PSScriptRoot "..\dist\PDF Suite\PDF Suite.exe"),
    [string] $OutputDirectory = (Join-Path $PSScriptRoot "..\.test-temp\visual-smoke")
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WindowPosition {
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
}
"@

$exe = (Resolve-Path -LiteralPath $Executable).Path
$pdf = (Resolve-Path -LiteralPath $PdfPath).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$process = Start-Process -FilePath $exe -ArgumentList ('"' + $pdf + '"') -PassThru

function Save-WindowShot([string] $Name, [int] $Width, [int] $Height) {
    [WindowPosition]::SetWindowPos($process.MainWindowHandle, [IntPtr]::Zero, 40, 40, $Width, $Height, 0) | Out-Null
    Start-Sleep -Milliseconds 500
    $bitmap = New-Object System.Drawing.Bitmap $Width, $Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen(40, 40, 0, 0, $bitmap.Size)
    $bitmap.Save((Join-Path $OutputDirectory "$Name.png"), [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose(); $bitmap.Dispose()
}

try {
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 200
        $process.Refresh()
        if ($process.HasExited) {
            throw "PDF Suite exited before opening a window (exit code $($process.ExitCode))."
        }
    } while ($process.MainWindowHandle -eq [IntPtr]::Zero -and [DateTime]::UtcNow -lt $deadline)

    if ($process.MainWindowHandle -eq [IntPtr]::Zero) {
        throw "PDF Suite did not open a main window within 20 seconds."
    }

    [Microsoft.VisualBasic.Interaction]::AppActivate($process.Id) | Out-Null
    Save-WindowShot "normal-1280x820" 1280 820
    [System.Windows.Forms.SendKeys]::SendWait("^d"); Start-Sleep -Milliseconds 400
    Save-WindowShot "details-1280x820" 1280 820
    [System.Windows.Forms.SendKeys]::SendWait("^%f"); Start-Sleep -Milliseconds 400
    Save-WindowShot "forms-1280x820" 1280 820
    [System.Windows.Forms.SendKeys]::SendWait("^%s"); Start-Sleep -Milliseconds 400
    Save-WindowShot "sign-1280x820" 1280 820
    Save-WindowShot "narrow-800x600" 800 600
    Save-WindowShot "compact-1024x768" 1024 768
}
finally {
    if (-not $process.HasExited) { $process.CloseMainWindow() | Out-Null }
}
