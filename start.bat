@echo off
chcp 65001 >nul
title SQL AI 智能查询助手

echo ========================================
echo   SQL AI 智能查询助手 - 一键启动
echo ========================================
echo.

echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python
    pause
    exit /b
)
echo [OK] Python 已安装

echo.
echo [2/4] 检查 Python 依赖...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    echo [OK] 依赖已就绪
)

echo.
echo [3/4] 检查 Ollama 服务...
curl -s http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo 启动 Ollama 服务...
    start /B ollama serve
    timeout /t 5 /nobreak >nul
)
echo [OK] Ollama 服务已运行

echo.
echo [4/4] 启动 Web 界面...
echo.
echo ========================================
echo   启动成功！
echo   访问地址: http://localhost:8501
echo   按 Ctrl+C 可停止服务
echo ========================================
echo.

streamlit run web_app_2.py --server.address localhost --server.port 8502

pause