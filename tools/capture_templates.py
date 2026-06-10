"""
牌面模板采集工具（图形化界面）。

用法:
  1. 启动雀魂并进入对局
  2. 运行: python -m tools.capture_templates
  3. 在图形窗口中按提示采集模板

采集的模板保存在 templates/tiles/ 目录。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    from majsoul_ai.ui.template_collector import run_template_collector
    run_template_collector()


if __name__ == "__main__":
    main()
