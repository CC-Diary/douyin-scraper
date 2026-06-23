@echo off
REM 设置 Windows 定时任务（任务计划程序）
REM 用法: setup-auto.bat [hour] [minute]
REM 例如: setup-auto.bat 9 0  (每天早上9点)

set HOUR=%1
set MINUTE=%2
if "%HOUR%"=="" set HOUR=9
if "%MINUTE%"=="" set MINUTE=0

set SCRIPT_DIR=%~dp0
set TASK_NAME=DouyinScraper

echo =========================================
echo   设置 Windows 定时抓取任务
echo =========================================
echo.

schtasks /create /tn "%TASK_NAME%" /tr "python \"%SCRIPT_DIR%scraper.py\" --transcribe" /sc daily /st %HOUR%:%MINUTE% /f

if %errorlevel% equ 0 (
    echo [OK] 定时任务已创建!
    echo     时间: 每天 %HOUR%:%MINUTE%
    echo     任务名: %TASK_NAME%
    echo.
    echo 管理命令:
    echo   查看: schtasks /query /tn %TASK_NAME%
    echo   删除: schtasks /delete /tn %TASK_NAME% /f
    echo   手动运行: python %SCRIPT_DIR%scraper.py --transcribe
) else (
    echo [!] 创建失败，请以管理员身份运行
)

echo.
pause
