@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    set "DRAW_PYTHON=python"
) else (
    set "DRAW_PYTHON=py -3"
)
%DRAW_PYTHON% --version >nul 2>nul
if errorlevel 1 (
    echo Python 3.9 or newer is required. Install Python, then run this launcher again.
    pause
    exit /b 1
)
:menu
cls
echo DRAW local updater - Vercel releases
echo.
echo 1. Check for updates
echo 2. Install latest update
echo 3. Roll back last update
echo 4. Recover interrupted update
echo 5. Exit
echo.
echo Save your artwork and close the editor before installing or rolling back.
choice /c 12345 /n /m "Choose: "
if errorlevel 5 exit /b 0
if errorlevel 4 goto recover
if errorlevel 3 goto rollback
if errorlevel 2 goto apply
%DRAW_PYTHON% "scripts\local_updater.py" check
goto done
:apply
%DRAW_PYTHON% "scripts\local_updater.py" apply
goto done
:rollback
%DRAW_PYTHON% "scripts\local_updater.py" rollback
goto done
:recover
%DRAW_PYTHON% "scripts\local_updater.py" recover
:done
echo.
pause
goto menu
