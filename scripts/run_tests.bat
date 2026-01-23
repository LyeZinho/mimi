@echo off
echo Running Mimi Tests...
echo =====================

python -m pytest tests/ -v

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] All tests passed!
) else (
    echo.
    echo [FAILURE] Some tests failed.
)
pause
