#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SQL AI 智能查询助手 - 一键启动器
支持 Windows / macOS / Linux
"""

import subprocess
import sys
import time
import os
import webbrowser
import requests
import threading

# 配置
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(PROJECT_DIR, "requirements.txt")
OLLAMA_URL = "http://localhost:11434"
STREAMLIT_PORT = 8502  # ✅ 改成 8502


def print_banner():
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║   🤖 SQL AI 智能查询助手 - 一键启动器               ║
    ║   Powered by Qwen2.5-7B + Streamlit + SQL Server    ║
    ╚═══════════════════════════════════════════════════════╝
    """)


def check_python():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or version.minor < 9:
        print(f"❌ Python 版本过低: {version.major}.{version.minor}")
        print("   请安装 Python 3.9 或更高版本")
        return False
    print(f"✅ Python {version.major}.{version.minor} 已就绪")
    return True


def install_dependencies():
    """安装 Python 依赖"""
    if not os.path.exists(REQUIREMENTS_FILE):
        print("⚠️  requirements.txt 不存在，跳过依赖安装")
        return True

    print("\n⏳ 检查 Python 依赖...")
    try:
        # 检查关键包是否已安装
        subprocess.run(
            [sys.executable, "-c", "import streamlit"],
            capture_output=True,
            check=True
        )
        print("✅ 依赖已就绪")
        return True
    except subprocess.CalledProcessError:
        print("⏳ 正在安装依赖，请稍候（约1-2分钟）...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE,
                 "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
                check=True
            )
            print("✅ 依赖安装完成")
            return True
        except subprocess.CalledProcessError:
            print("❌ 依赖安装失败，请手动运行: pip install -r requirements.txt")
            return False


def check_ollama():
    """检查 Ollama 服务是否运行"""
    try:
        response = requests.get(OLLAMA_URL, timeout=3)
        return response.status_code == 200
    except:
        return False


def start_ollama():
    """启动 Ollama 服务"""
    print("\n⏳ 启动 Ollama 服务...")
    try:
        if sys.platform == "win32":
            # Windows: 后台启动
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # macOS / Linux
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        # 等待服务启动
        print("⏳ 等待 Ollama 服务启动（10秒）...")
        for i in range(10):
            time.sleep(1)
            if check_ollama():
                print("✅ Ollama 服务已启动")
                return True
        return False
    except FileNotFoundError:
        print("❌ 未找到 Ollama 命令")
        print("   请访问 https://ollama.ai 下载安装")
        return False


def start_streamlit():
    """启动 Streamlit 应用"""
    print(f"\n⏳ 启动 Web 界面...")
    print("=" * 50)
    print("  ✅ 启动成功！")
    print(f"  🌐 访问地址: http://localhost:{STREAMLIT_PORT}")
    print("  ⌨️  按 Ctrl+C 可停止服务")
    print("=" * 50)
    print()

    # 自动打开浏览器
    def open_browser():
        time.sleep(2)
        webbrowser.open(f"http://localhost:{STREAMLIT_PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    # 启动 Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "web_app_2.py",  # ✅ 改成 web_app_2.py
            "--server.address", "localhost",
            "--server.port", str(STREAMLIT_PORT)
        ])
    except KeyboardInterrupt:
        print("\n\n👋 已停止服务")


def main():
    os.chdir(PROJECT_DIR)
    print_banner()

    # 1. 检查 Python
    if not check_python():
        input("按回车键退出...")
        return

    # 2. 安装依赖
    if not install_dependencies():
        input("按回车键退出...")
        return

    # 3. 检查 Ollama
    if not check_ollama():
        if not start_ollama():
            input("按回车键退出...")
            return
    else:
        print("✅ Ollama 服务已运行")

    # 4. 启动 Streamlit
    start_streamlit()


if __name__ == "__main__":
    main()