@echo off
setlocal
@REM ############################################################################## PYTHON VERSION VERY IMPORTANT
@REM set "python_version=39"
set "python_version=312"
@REM ############################################################################## other variables
:: Get the user directory 
set "userdir=%userprofile%"
@REM ############################################################################## Activate local env
cd %userdir%\scripts\OctoPrint
set "folder=%cd%"
:: Get the user directory 
set "userdir=%userprofile%"
for %%A in ("%folder%") do set "folder=%%~nxA"
set "name=%folder%-py%python_version%-env"
if exist "%userdir%\envs\%name%" (
    echo Enabling venv
) else (
    echo No venv. Run local_setup first.
    exit /b 1
)
set "path=%userdir%\envs\%name%\Scripts\activate.bat"
start cmd.exe /k %path%