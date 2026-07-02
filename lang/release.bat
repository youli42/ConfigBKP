@echo off
REM Compile all .ts files to .qm for distribution
REM Requires PySide6 (pyside6-lrelease)

set LANG_DIR=%~dp0
set VENV_DIR=%~dp0..\.venv

if exist "%VENV_DIR%\Scripts\pyside6-lrelease.exe" (
    set LRELEASE="%VENV_DIR%\Scripts\pyside6-lrelease.exe"
) else (
    set LRELEASE="pyside6-lrelease"
)

echo Compiling .ts -> .qm ...
for %%f in ("%LANG_DIR%*.ts") do (
    if not "%%~nf"=="zh_CN" (
        echo   %%~nf.ts ...
        %LRELEASE% "%%f" -qm "%LANG_DIR%%%~nf.qm"
    )
)
echo Done.
