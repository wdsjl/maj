"""便携版入口：启动菜单。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def main() -> None:
    if getattr(sys, "frozen", False):
        # PyInstaller 解压目录
        base = Path(sys.executable).parent
        python = sys.executable
        cwd = base
    else:
        base = ROOT
        python = sys.executable
        cwd = base

    menu = """
  雀魂 AI 助手（便携版）
  [1] 采集牌面模板
  [2] 启动 AI 助手
  [0] 退出
"""
    while True:
        print(menu)
        choice = input("请选择: ").strip()
        if choice == "1":
            subprocess.run([python, "-m", "tools.capture_templates"], cwd=cwd)
        elif choice == "2":
            subprocess.run([python, "-m", "majsoul_ai"], cwd=cwd)
        elif choice == "0":
            break


if __name__ == "__main__":
    main()
