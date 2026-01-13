@echo off
setlocal enabledelayedexpansion
for /f %%a in ('echo prompt $E^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "RESET=%ESC%[0m"
set "NO_CACHE=0"
set "GDS_FILE="
:parse_args
if "%~1"=="" goto check_args
if /i "%~1"=="--no-cache" (
    set "NO_CACHE=1"
    shift
    goto parse_args
)
if /i "%~1"=="-c" (
    set "GDS_FILE=%~2"
    shift
    shift
    goto parse_args
)
shift
goto parse_args

:check_args
if "%GDS_FILE%"=="" (
    echo GDS Version: 1.0
    echo GDS Github: https://github.com/AverageMaipuperson/GDS
    echo Compile: gds -c "file.gds" [--no-cache]
    exit /b 1
)

if not exist "%GDS_FILE%" (
    echo %RED%FATAL: The file you provided: "%GDS_FILE%" does not exist.%RESET%
    exit /b 1
)

if /i not "%~x2"==".gds" (
    for %%F in ("%GDS_FILE%") do set "EXT=%%~xF"
    if /i not "!EXT!"==".gds" (
        echo %RED%FATAL: The file you provided: "%GDS_FILE%" does not have the file format .gds%RESET%
        exit /b 1
    )
)
for %%i in ("%GDS_FILE%") do set "CURRENT_MOD=%%~ti"
set "STATE_FILE=%GDS_FILE%.lastmod"
if "!NO_CACHE!"=="0" (
    if exist "!STATE_FILE!" (
        set /p LAST_MOD=<"!STATE_FILE!"
        if "!CURRENT_MOD!"=="!LAST_MOD!" (
            echo GDS: no work to do.
            exit /b 0
        )
    )
)

for %%G in ("%~dp0..") do set "PARENT=%%~fG"
python "%PARENT%\compile.py" "%GDS_FILE%"

if %errorlevel% equ 0 (
    echo !CURRENT_MOD!>"!STATE_FILE!"
)
