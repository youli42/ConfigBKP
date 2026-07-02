$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$DistDir = Join-Path $ProjectRoot "dist"
$IconPath = Join-Path $ProjectRoot "resources\icons\app.ico"

$PyInstaller = "pyinstaller"

$Version = "1.5.0"
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
    # 复制 lang/ 到 _internal/ 目录
    $LangDest = Join-Path $OutDir "_internal" "lang"
    if (Test-Path $LangDest) {
        Remove-Item -Path $LangDest -Recurse -Force
    }
    New-Item -ItemType Directory -Path (Join-Path $OutDir "_internal") -Force | Out-Null
    Copy-Item -Path (Join-Path $ProjectRoot "lang") -Destination (Join-Path $OutDir "_internal") -Recurse
    Write-Host "打包成功! 输出: $OutDir" -ForegroundColor Green
    Write-Host "目录结构:" -ForegroundColor Cyan
    Get-ChildItem -Path $OutDir -Name
}
catch {
    Write-Host "打包失败: $_" -ForegroundColor Red
    exit 1
}
