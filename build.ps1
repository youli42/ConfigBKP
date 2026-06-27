$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$DistDir = Join-Path $ProjectRoot "dist"
$IconPath = Join-Path $ProjectRoot "resources\icons\app.ico"

if (-not (Test-Path $IconPath)) {
    Write-Warning "图标文件不存在，将使用默认图标: $IconPath"
    $IconPath = $null
}

$PyInstaller = "pyinstaller"

$Version = "1.0.0"
$OutName = "WinConfigBKP-$Version"

Write-Host "正在打包 WinConfigBKP v$Version ..." -ForegroundColor Cyan

$args = @(
    "--onefile"
    "--windowed"
    "--name", $OutName
    "--distpath", $DistDir
    "--add-data", "config;config"
    "--hidden-import", "json5"
    "--hidden-import", "PySide6.QtCore"
    "--hidden-import", "PySide6.QtWidgets"
    "--hidden-import", "PySide6.QtGui"
    (Join-Path $ProjectRoot "main.py")
)

if ($IconPath) {
    $args = @("--icon", $IconPath) + $args
}

try {
    & $PyInstaller @args
    Write-Host "打包成功! 输出: $DistDir\$OutName.exe" -ForegroundColor Green
}
catch {
    Write-Host "打包失败: $_" -ForegroundColor Red
    exit 1
}
