$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$DistDir = Join-Path $ProjectRoot "dist"
$IconPath = Join-Path $ProjectRoot "resources\icons\app.ico"

$PyInstaller = "pyinstaller"

$Version = "1.0.0"
$OutName = "WinConfigBKP-$Version"

Write-Host "正在打包 WinConfigBKP v$Version ..." -ForegroundColor Cyan

$args = @(
    "--onedir"
    "--windowed"
    "--name", $OutName
    "--distpath", $DistDir
    "--hidden-import", "json5"
    "--hidden-import", "PySide6.QtCore"
    "--hidden-import", "PySide6.QtWidgets"
    "--hidden-import", "PySide6.QtGui"
    (Join-Path $ProjectRoot "main.py")
)

if (Test-Path $IconPath) {
    $args = @("--icon", $IconPath) + $args
}

try {
    & $PyInstaller @args
    $OutDir = Join-Path $DistDir $OutName
    # 复制 config/ 到 exe 同目录，实现便携式
    $ConfigDest = Join-Path $OutDir "config"
    if (Test-Path $ConfigDest) {
        Remove-Item -Path $ConfigDest -Recurse -Force
    }
    Copy-Item -Path (Join-Path $ProjectRoot "config") -Destination $OutDir -Recurse
    Write-Host "打包成功! 输出: $OutDir" -ForegroundColor Green
    Write-Host "目录结构:" -ForegroundColor Cyan
    Get-ChildItem -Path $OutDir -Name
}
catch {
    Write-Host "打包失败: $_" -ForegroundColor Red
    exit 1
}
