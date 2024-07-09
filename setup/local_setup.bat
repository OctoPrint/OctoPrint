@echo off
setlocal
echo =================================
echo Welcome to setup. This setup will create local virtual env
echo And then it install required python libraries from req.txt file in current directory
echo you can rerun this without any issue
@REM ############################################################################## notes
@REM python 3.12 tested
@REM ############################################################################## PYTHON VERSION VERY IMPORTANT
set "python_version=312"
echo Using Python %python_version%
@REM ############################################################################## other variables
:: Get the user directory 
set "userdir=%userprofile%"
@REM ############################################################################## Python exe
if exist "%userdir%\AppData\Local\Programs\Python\Python%python_version%\python.exe" (
    set python_exe="%userdir%\AppData\Local\Programs\Python\Python%python_version%\python.exe"
) else (
    if exist "C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python%python_version%_64\python.exe" (
        set python_exe="C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python%python_version%_64\python.exe"
    ) else (
        exit
    )
)
@REM ##############################################################################
cd %userdir%\scripts\OctoPrint
set "folder=%cd%"
for %%A in ("%folder%") do set "folder=%%~nxA"
set "name=%folder%-py%python_version%-env"
if exist "%userdir%\envs\%name%" (
    echo "%userdir%\envs\%name%" folder exists
) else (
    echo Creating envs
    %python_exe% -m venv "%userdir%\envs\%name%"
)
call %userdir%\envs\%name%\Scripts\activate
python -m pip install --upgrade pip
@REM ##############################################################################
@REM for python version specific
@REM if exist req%python_version%_win.txt (
@REM     python -m pip install -r req%python_version%_win.txt
@REM )
@REM ##############################################################################
deactivate