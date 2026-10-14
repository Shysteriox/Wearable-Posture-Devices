@echo off
echo ==============================================
echo Building Posture Visualizer Standalone Exe
echo ==============================================
echo.

cd /d "%~dp0"

echo [1/3] Checking if PyInstaller is installed...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing now...
    pip install pyinstaller pandas matplotlib customtkinter
)

echo.
echo [2/3] Compiling visualizer.py to standalone executable...
echo (This may take a minute)
echo.

pyinstaller --noconfirm --onefile --name "WristPostureVisualizer" "visualizer.py"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyInstaller compilation failed!
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Done! Executable created successfully.
echo You can find it inside:
echo "%~dp0dist\WristPostureVisualizer.exe"
echo.
echo You can right-click "WristPostureVisualizer.exe" to pin it to your taskbar!
echo.
pause
