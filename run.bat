@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Изоляция временных файлов
set "TEMP=%SCRIPT_DIR%temp"
set "TMP=%SCRIPT_DIR%temp"
set "GRADIO_TEMP_DIR=%SCRIPT_DIR%temp"

:: Изоляция кэша HuggingFace
set "HF_HOME=%SCRIPT_DIR%models"
set "HUGGINGFACE_HUB_CACHE=%SCRIPT_DIR%models"
set "TRANSFORMERS_CACHE=%SCRIPT_DIR%models"
set "HF_DATASETS_CACHE=%SCRIPT_DIR%models\datasets"

:: Изоляция кэша PyTorch
set "TORCH_HOME=%SCRIPT_DIR%models\torch"

:: Изоляция общего кэша
set "XDG_CACHE_HOME=%SCRIPT_DIR%cache"

:: FFmpeg в PATH
if exist "%SCRIPT_DIR%ffmpeg" (
    set "PATH=%SCRIPT_DIR%ffmpeg;%PATH%"
)

:: Кодировка
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
set "PYTHONPATH=%SCRIPT_DIR%"

:: Проверка установки
if not exist "python\python.exe" (
    echo.
    echo ОШИБКА: Python не найден!
    echo Сначала запустите install.bat для установки.
    echo.
    pause
    exit /b 1
)

if not exist "app.py" (
    echo.
    echo ОШИБКА: Файл app.py не найден!
    echo Убедитесь, что файлы приложения на месте.
    echo.
    pause
    exit /b 1
)

:: Чтение конфигурации GPU
if exist "cuda_version.txt" (
    set /p CUDA_VER=<cuda_version.txt
    echo Конфигурация GPU: !CUDA_VER!
) else (
    echo ПРЕДУПРЕЖДЕНИЕ: cuda_version.txt не найден. Используется конфигурация по умолчанию.
)

echo.
echo ============================================================
echo    LavaSR Portable - Запуск
echo    Улучшение и суперразрешение аудио
echo ============================================================
echo.
echo  Интерфейс откроется в браузере автоматически.
echo  Для остановки нажмите Ctrl+C или закройте это окно.
echo.

python\python.exe app.py

if errorlevel 1 goto :app_error
goto :eof

:app_error
echo.
echo ============================================================
echo    ОШИБКА при запуске приложения
echo ============================================================
echo.
echo  Возможные причины:
echo.
echo  1. Недостаточно видеопамяти VRAM
echo     - Закройте другие приложения, использующие GPU
echo     - Попробуйте переустановить с выбором CPU
echo.
echo  2. Проблемы с CUDA
echo     - Убедитесь, что установлены последние драйверы NVIDIA
echo     - Переустановите с правильной версией CUDA
echo.
echo  3. Отсутствуют зависимости
echo     - Запустите install.bat заново
echo.
pause
