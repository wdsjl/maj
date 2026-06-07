"""配置加载。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 相对路径转绝对路径
    templates = ROOT / cfg["paths"]["templates_dir"]
    cfg["paths"]["templates_dir"] = str(templates)
    align = cfg["paths"].get("alignment_template", "")
    if align and not Path(align).is_absolute():
        cfg["paths"]["alignment_template"] = str(ROOT / align)
    return cfg
