@echo off
setlocal enabledelayedexpansion
for /f %%a in ('echo prompt $E^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "RESET=%ESC%[0m"
if "%~1"=="" (
    echo GDS Version: 1.0
    echo GDS Github: https://github.com/AverageMaipuperson/GDS
    echo Compile: gds -c "file.gds"
    exit /b 1
)
if /i "%~1"=="-c" (
    if "%~2"=="" (
        echo %RED%FATAL: No .gds file provided.%RESET%
        echo Compiling process stopped.
        exit /b 1
    )
    if not exist "%~2" (
        echo %RED%FATAL: The file you provided: "%~2" does not exist.%RESET%
        echo Compiling process stopped.
        exit /b 1
    )
)

if /i not "%~x2"==".gds" (
    echo %RED%FATAL: The file you provided: "%~2" does not have the file format .gds%RESET%
    echo Compiling process stopped.
    exit /b 1
)

for %%i in ("%~2") do set "CURRENT_MOD=%%~ti"
set "STATE_FILE=%~2.lastmod"
if exist "!STATE_FILE!" (
    set /p LAST_MOD=<"!STATE_FILE!"
    if "!CURRENT_MOD!"=="!LAST_MOD!" (
        echo GDS: no work to do.
        exit /b 0
    )
)
for %%G in ("%~dp0..") do set "PARENT=%%~fG"
python "%PARENT%\gds\compile.py" "%~2"
if %errorlevel% equ 0 (
    echo !CURRENT_MOD!>"!STATE_FILE!"
)
