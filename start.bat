@echo off
title Git差异提取工具

echo 正在启动Git差异提取工具...
echo.

:: 检查是否安装了uv
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到uv包管理器
    echo 请先安装uv: pip install uv
    pause
    exit /b 1
)

:: 运行主程序
uv run python src/main.py

:: 如果程序异常退出，显示错误信息
if %errorlevel% neq 0 (
    echo.
    echo 程序异常退出，错误代码: %errorlevel%
    pause
)