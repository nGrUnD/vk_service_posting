@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  VK Service Posting — загрузка клипов по vk_pages.txt
echo  =====================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [Ошибка] Не найден Python. Установите Python 3.10+ с https://www.python.org/downloads/
    echo        При установке отметьте "Add python.exe to PATH".
    pause
    exit /b 1
)

pip show yt-dlp >nul 2>&1
if errorlevel 1 (
    echo Устанавливаю yt-dlp...
    pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [Ошибка] Не удалось установить зависимости.
        pause
        exit /b 1
    )
)

set "INPUT=%~1"
if not defined INPUT if exist "%~dp0..\vk_pages.txt" set "INPUT=%~dp0..\vk_pages.txt"
if not defined INPUT (
    set /p "INPUT=Путь к vk_pages.txt или папке с архивом: "
    if "!INPUT!"=="" (
        echo Укажите файл или перетащите vk_pages.txt на этот bat-файл.
        pause
        exit /b 1
    )
)

echo.
python "%~dp0download_vk_clips.py" --input "!INPUT!"
set "ERR=!ERRORLEVEL!"
echo.
if "!ERR!"=="0" (
    echo Загрузка завершена.
) else (
    echo Завершено с ошибками. См. папку clips\errors.txt
)
pause
exit /b !ERR!
