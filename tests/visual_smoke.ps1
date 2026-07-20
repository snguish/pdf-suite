param(
    [Parameter(Mandatory = $true)] [string] $PdfPath,
    [string] $Executable = (Join-Path $PSScriptRoot "..\dist\PDF Suite\PDF Suite.exe"),
    [string] $OutputDirectory = (Join-Path $PSScriptRoot "..\.test-temp\visual-smoke"),
    [int] $CommentPointX = -1,
    [int] $CommentPointY = -1,
    [int] $CropStartX = -1,
    [int] $CropStartY = -1,
    [int] $CropEndX = -1,
    [int] $CropEndY = -1
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
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
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
    Start-Sleep -Milliseconds 1000
    Save-WindowShot "normal-1280x820" 1280 820
    [System.Windows.Forms.SendKeys]::SendWait("{F1}"); Start-Sleep -Milliseconds 500
    Save-WindowShot "user-guide-1280x820" 1280 820
    [System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("h"); Start-Sleep -Milliseconds 400
    Save-WindowShot "highlight-1280x820" 1280 820
    [System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("c"); Start-Sleep -Milliseconds 400
    if ($CropStartX -ge 0 -and $CropStartY -ge 0 -and $CropEndX -ge 0 -and $CropEndY -ge 0) {
        [WindowPosition]::SetCursorPos(40 + $CropStartX, 40 + $CropStartY) | Out-Null
        [WindowPosition]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
        1..12 | ForEach-Object {
            $x = [int](40 + $CropStartX + (($CropEndX - $CropStartX) * $_ / 12))
            $y = [int](40 + $CropStartY + (($CropEndY - $CropStartY) * $_ / 12))
            [WindowPosition]::SetCursorPos($x, $y) | Out-Null
            Start-Sleep -Milliseconds 25
        }
        [WindowPosition]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 300
    }
    Save-WindowShot "crop-1280x820" 1280 820
    [System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("^d"); Start-Sleep -Milliseconds 400
    Save-WindowShot "details-1280x820" 1280 820
    if ($CommentPointX -ge 0 -and $CommentPointY -ge 0) {
        [WindowPosition]::SetCursorPos(40 + $CommentPointX, 40 + $CommentPointY) | Out-Null
        1..2 | ForEach-Object {
            [WindowPosition]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
            [WindowPosition]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
            Start-Sleep -Milliseconds 80
        }
        Start-Sleep -Milliseconds 500
        Save-WindowShot "comment-1280x820" 1280 820
    }
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
