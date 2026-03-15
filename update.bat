@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ============================================================
echo    LavaSR Portable - Обновление
echo ============================================================
echo.

:: Проверка наличия git
where git >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Git не найден!
    echo Установите Git с https://git-scm.com/
    echo Или скачайте обновление вручную.
    echo.
    pause
    exit /b 1
)

:: Проверка наличия .git
if not exist ".git" (
    echo ОШИБКА: Это не git-репозиторий!
    echo Обновление через git невозможно.
    echo Скачайте новую версию вручную.
    echo.
    pause
    exit /b 1
)

echo Получение обновлений...
git pull
if errorlevel 1 (
    echo.
    echo ПРЕДУПРЕЖДЕНИЕ: Не удалось обновить.
    echo Возможные причины: нет интернета или есть локальные изменения.
    echo.
) else (
    echo.
    echo Обновление завершено!
    echo.
)

pause
