@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Сборка VK Clips Downloader.exe ...
echo.

where py >nul 2>&1
if errorlevel 1 (
    set PY=python
) else (
    set PY=py -3.11
)

%PY% --version >nul 2>&1
if errorlevel 1 (
    echo Установите Python 3.11+ и добавьте в PATH.
    pause
    exit /b 1
)

%PY% -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

%PY% -m PyInstaller --noconfirm "VK Clips Downloader.spec"

if errorlevel 1 (
    echo Сборка не удалась.
    pause
    exit /b 1
)

echo.
echo Готово: dist\VK Clips Downloader.exe
echo Скопируйте exe пользователю — Python не нужен.
echo.
pause
