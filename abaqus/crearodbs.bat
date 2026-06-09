@echo off
setlocal enabledelayedexpansion

for /f %%i in (listainps.txt) do (
    abaqus job=%%~ni input=%%i cpus=16 interactive
)

pause