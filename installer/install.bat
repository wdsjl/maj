@echo off
chcp 65001 >nul
title 雀魂 AI 助手 - 一键安装
cd /d "%~dp0.."
echo.
echo  正在启动安装程序，请稍候...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
    echo.
    echo  安装失败，请查看上方错误信息。
    pause
    exit /b 1
)
pause
