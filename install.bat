@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "TEMP=%SCRIPT_DIR%temp"
set "TMP=%SCRIPT_DIR%temp"

echo ============================================================
echo    LavaSR Portable - Установка
echo    Улучшение и суперразрешение аудио
echo ============================================================
echo.

:: Создание директорий
if not exist "python" mkdir python
if not exist "downloads" mkdir downloads
if not exist "temp" mkdir temp
if not exist "models" mkdir models
if not exist "cache" mkdir cache
if not exist "output" mkdir output

echo ============================================================
echo    Шаг 1: Выбор видеокарты
echo ============================================================
echo.
echo  Выберите вашу видеокарту:
echo.
echo  [1] NVIDIA GTX 10xx (Pascal)       - CUDA 11.8
echo  [2] NVIDIA RTX 20xx (Turing)       - CUDA 11.8
echo  [3] NVIDIA RTX 30xx (Ampere)       - CUDA 12.6
echo  [4] NVIDIA RTX 40xx (Ada Lovelace) - CUDA 12.8
echo  [5] NVIDIA RTX 50xx (Blackwell)    - CUDA 12.8
echo  [6] Без GPU (только CPU)
echo.

set /p GPU_CHOICE="Введите номер [1-6]: "

if "%GPU_CHOICE%"=="1" (
    set "CUDA_VERSION=cu118"
    set "TORCH_VERSION=2.7.1"
    set "CUDA_LABEL=CUDA 11.8"
)
if "%GPU_CHOICE%"=="2" (
    set "CUDA_VERSION=cu118"
    set "TORCH_VERSION=2.7.1"
    set "CUDA_LABEL=CUDA 11.8"
)
if "%GPU_CHOICE%"=="3" (
    set "CUDA_VERSION=cu126"
    set "TORCH_VERSION=2.7.1"
    set "CUDA_LABEL=CUDA 12.6"
)
if "%GPU_CHOICE%"=="4" (
    set "CUDA_VERSION=cu128"
    set "TORCH_VERSION=2.7.1"
    set "CUDA_LABEL=CUDA 12.8"
)
if "%GPU_CHOICE%"=="5" (
    set "CUDA_VERSION=cu128"
    set "TORCH_VERSION=2.7.1"
    set "CUDA_LABEL=CUDA 12.8"
)
if "%GPU_CHOICE%"=="6" (
    set "CUDA_VERSION=cpu"
    set "TORCH_VERSION=2.8.0"
    set "CUDA_LABEL=CPU"
)

if not defined CUDA_VERSION (
    echo ОШИБКА: Неверный выбор. Запустите установку заново.
    pause
    exit /b 1
)

echo.
echo Выбрано: !CUDA_LABEL!
echo.

:: ============================================================
echo ============================================================
echo    Шаг 2: Установка портативного Python 3.12.8
echo ============================================================
echo.

if exist "python\python.exe" (
    echo Python уже установлен, пропускаем...
    goto :step3
)

echo Скачивание Python 3.12.8 Embeddable...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip' -OutFile 'downloads\python-3.12.8-embed-amd64.zip'"
if errorlevel 1 (
    echo ОШИБКА: Не удалось скачать Python!
    pause
    exit /b 1
)

echo Распаковка Python...
powershell -Command "Expand-Archive -Path 'downloads\python-3.12.8-embed-amd64.zip' -DestinationPath 'python' -Force"
if errorlevel 1 (
    echo ОШИБКА: Не удалось распаковать Python!
    pause
    exit /b 1
)

:step3
:: ============================================================
echo ============================================================
echo    Шаг 3: Настройка Python и pip
echo ============================================================
echo.

:: Патч python312._pth для включения site-packages
(
    echo import site
    echo.
    echo python312.zip
    echo .
    echo ..\Lib\site-packages
) > "python\python312._pth"

if exist "python\Scripts\pip.exe" (
    echo pip уже установлен, пропускаем...
    goto :step4
)

echo Установка pip...
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'downloads\get-pip.py'"
if errorlevel 1 (
    echo ОШИБКА: Не удалось скачать get-pip.py!
    pause
    exit /b 1
)

python\python.exe downloads\get-pip.py --no-warn-script-location
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить pip!
    pause
    exit /b 1
)

:step4
:: ============================================================
echo ============================================================
echo    Шаг 4: Установка PyTorch - !CUDA_LABEL!
echo ============================================================
echo.

if "!CUDA_VERSION!"=="cpu" goto :pytorch_cpu

echo Установка PyTorch !TORCH_VERSION! - !CUDA_LABEL!...
python\python.exe -m pip install torch==!TORCH_VERSION! torchaudio --index-url https://download.pytorch.org/whl/!CUDA_VERSION! --no-warn-script-location
goto :pytorch_done

:pytorch_cpu
echo Установка PyTorch !TORCH_VERSION! - CPU...
python\python.exe -m pip install torch==!TORCH_VERSION! torchaudio --index-url https://download.pytorch.org/whl/cpu --no-warn-script-location

:pytorch_done
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить PyTorch!
    pause
    exit /b 1
)

:: ============================================================
echo ============================================================
echo    Шаг 5: Установка LavaSR и зависимостей
echo ============================================================
echo.

echo Установка vocos - кастомный форк...
python\python.exe -m pip install https://github.com/langtech-bsc/vocos/archive/refs/heads/matcha.zip --no-warn-script-location
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить vocos!
    pause
    exit /b 1
)

echo Установка LavaSR...
python\python.exe -m pip install https://github.com/ysharma3501/LavaSR/archive/refs/heads/main.zip --no-warn-script-location
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить LavaSR!
    pause
    exit /b 1
)

echo Установка остальных зависимостей...
python\python.exe -m pip install -r requirements.txt --no-warn-script-location
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить зависимости!
    pause
    exit /b 1
)

:: ============================================================
echo ============================================================
echo    Шаг 6: Установка FFmpeg
echo ============================================================
echo.

if exist "ffmpeg\ffmpeg.exe" (
    echo FFmpeg уже установлен, пропускаем...
    goto :step7
)

if not exist "ffmpeg" mkdir ffmpeg

echo Скачивание FFmpeg...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'downloads\ffmpeg.zip'"
if errorlevel 1 (
    echo ПРЕДУПРЕЖДЕНИЕ: Основной источник недоступен. Пробуем альтернативный...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'downloads\ffmpeg.zip'"
)

if not exist "downloads\ffmpeg.zip" (
    echo ПРЕДУПРЕЖДЕНИЕ: FFmpeg не установлен. Некоторые форматы аудио могут не поддерживаться.
    goto :step7
)

echo Распаковка FFmpeg...
powershell -Command "Expand-Archive -Path 'downloads\ffmpeg.zip' -DestinationPath 'downloads\ffmpeg_extract' -Force"

for /r "downloads\ffmpeg_extract" %%f in (ffmpeg.exe) do (
    copy "%%f" "ffmpeg\ffmpeg.exe" >nul 2>&1
)
for /r "downloads\ffmpeg_extract" %%f in (ffprobe.exe) do (
    copy "%%f" "ffmpeg\ffprobe.exe" >nul 2>&1
)

if exist "downloads\ffmpeg_extract" rmdir /s /q "downloads\ffmpeg_extract"

:step7
:: ============================================================
echo ============================================================
echo    Шаг 7: Сохранение конфигурации
echo ============================================================
echo.

echo !CUDA_VERSION!> cuda_version.txt
echo Конфигурация GPU сохранена: !CUDA_LABEL!

:: Очистка
if exist "downloads\python-3.12.8-embed-amd64.zip" del "downloads\python-3.12.8-embed-amd64.zip"
if exist "downloads\get-pip.py" del "downloads\get-pip.py"
if exist "downloads\ffmpeg.zip" del "downloads\ffmpeg.zip"

echo.
echo ============================================================
echo    Установка завершена!
echo ============================================================
echo.
echo  Для запуска используйте: run.bat
echo.
pause
