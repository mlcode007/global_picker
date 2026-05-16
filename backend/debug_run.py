"""
PyCharm 调试启动脚本

使用方式：
1. 在 PyCharm 中右键此文件 → "Run 'debug_run'" 或 "Debug 'debug_run'"
2. 或者配置 Run/Debug Configuration：
   - Script path: backend/debug_run.py
   - Working directory: backend
   - Python interpreter: 项目虚拟环境

调试技巧：
- 在任意代码行打断点，Debug 模式下会自动暂停
- 使用 Debug 面板查看变量、调用栈
- 使用 Evaluate Expression 执行任意 Python 表达式
"""
import sys
import os
import subprocess
import signal

# 确保 backend 目录在 sys.path 中
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn


def kill_port(port: int):
    """杀掉占用指定端口的进程。"""
    try:
        # macOS: lsof -ti :8000 | xargs kill -9
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            print(f"发现端口 {port} 被占用，正在清理进程: {', '.join(pids)}")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
            # 等 1 秒让进程退出
            import time
            time.sleep(1)
            # 如果还在，强制 kill
            result2 = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True, timeout=5
            )
            if result2.stdout.strip():
                for pid in result2.stdout.strip().split("\n"):
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                print(f"已强制清理端口 {port}")
            else:
                print(f"端口 {port} 已释放")
        else:
            print(f"端口 {port} 未被占用")
    except Exception as e:
        print(f"清理端口 {port} 时出错: {e}")


if __name__ == "__main__":
    # 启动前先清理 8000 端口
    kill_port(8000)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,       # 代码修改后自动重载
        log_level="info",
    )
