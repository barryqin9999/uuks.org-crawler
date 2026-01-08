@echo off
cd /d "%~dp0"

echo ========================================================
echo   UUKS Auto Installer (Full Auto Mode)
echo ========================================================
echo.

:: --- CONFIGURATION ---
set "PY_VER=3.10.11"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-embed-amd64.zip"
set "PY_DIR=%~dp0python"
set "PY_EXE=%PY_DIR%\python.exe"

:: ----------------------------------------------------------
:: STEP 1: Check and Install Python (Embeddable)
:: ----------------------------------------------------------
echo [Step 1] Checking Python environment...

if exist "%PY_EXE%" (
    echo [OK] Python found in local folder.
) else (
    echo [INFO] Python not found. Downloading Python %PY_VER%...
    echo        (This may take a minute depending on your internet)
    
    :: Download Python Zip
    powershell -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile 'python.zip'"
    
    if not exist "python.zip" (
        echo [ERROR] Failed to download Python. Please check internet connection.
        pause
        exit
    )
    
    echo [INFO] Unzipping Python...
    powershell -Command "Expand-Archive -Path 'python.zip' -DestinationPath '%PY_DIR%' -Force"
    
    del "python.zip"
    
    if not exist "%PY_EXE%" (
        echo [ERROR] Unzip failed or python.exe missing.
        pause
        exit
    )
    echo [OK] Python installed successfully.
)

:: ----------------------------------------------------------
:: STEP 2: Configure ._pth file (Critical Fix)
:: ----------------------------------------------------------
echo.
echo [Step 2] Configuring python path (._pth file)...
cd "%PY_DIR%"
:: Uncomment 'import site' and add '..' to path
powershell -Command "Get-ChildItem *._pth | ForEach-Object { $c = Get-Content $_; $c = $c -replace '#import site', 'import site'; if ($c -notcontains '..') { $c += '..' }; Set-Content $_ $c }"
cd "%~dp0"
echo [OK] Path configured.

:: ----------------------------------------------------------
:: STEP 3: Install PIP
:: ----------------------------------------------------------
echo.
echo [Step 3] Checking PIP...
"%PY_EXE%" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] PIP not found. Downloading get-pip.py...
    powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile 'get-pip.py'"
    
    echo [INFO] Installing PIP...
    "%PY_EXE%" "get-pip.py" --no-warn-script-location
    del "get-pip.py"
)
echo [OK] PIP is ready.

:: ----------------------------------------------------------
:: STEP 4: Install Requirements
:: ----------------------------------------------------------
echo.
echo [Step 4] Installing libraries from requirements.txt...
if exist "requirements.txt" (
    "%PY_EXE%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location
) else (
    echo [WARNING] requirements.txt not found! Skipping library install.
)

:: ----------------------------------------------------------
:: STEP 5: Create Launcher
:: ----------------------------------------------------------
echo.
echo [Step 5] Creating 'start.bat'...
(
    echo @echo off
    echo "%PY_DIR%\python.exe" "main.py"
    echo pause
) > start.bat

echo.
echo ========================================================
echo   INSTALLATION COMPLETE!
echo ========================================================
echo Please run 'start.bat' to use the software.
echo.
pause
