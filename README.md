# 雀魂麻将 AI 实时分析助手 (Majsoul AI Overlay)

基于 **屏幕捕捉 + 牌面识别 + Mortal AI** 的雀魂（Mahjong Soul）实时出牌建议工具。在 Windows 客户端上捕捉游戏窗口，识别牌面，通过 MJAI 协议接入 [Mortal](https://github.com/Equim-chan/Mortal) 引擎，并以**透明悬浮窗**显示最优出牌策略。

> **免责声明**：本工具仅供学习研究。使用第三方辅助工具可能违反雀魂服务条款，导致账号封禁。请自行承担风险。

## 功能

- Windows 雀魂窗口自动捕捉（支持中英文客户端窗口标题）
- 画面配准到标准 1280×720 坐标系，适配不同分辨率
- 基于模板匹配的牌面识别（可扩展为深度学习模型）
- **四家牌河识别**：按出牌顺序扫描各玩家牌河
- **副露识别**：吃/碰/杠区域扫描与 MJAI 事件生成
- **完整 MJAI 状态重建**：从视觉快照重建完整事件流（start_kyoku → tsumo/dahai/副露）
- 接入 Mortal 子进程；不可用时降级为简易 bot
- PyQt6 透明悬浮窗，显示推荐出牌及备选方案
- 模板采集工具，方便自行校准牌面

## 系统要求

- **Windows 10/11**（窗口捕捉依赖 Win32 API）
- Python 3.10+
- （可选）[Mortal](https://github.com/Equim-chan/Mortal) 及模型权重 `mortal.pth`

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Mortal（可选但推荐）

1. 按 [Mortal 文档](https://mortal.ekyu.moe/user/build.html) 编译安装
2. 获取模型权重（参见 Akagi / Mortal 社区）
3. 编辑 `config/default.yaml`：

```yaml
mortal:
  root: "C:/path/to/Mortal"
  model_path: "C:/path/to/mortal.pth"
  player_id: 0
  fallback_bot: true
```

### 3. 采集牌面模板

```bash
python -m tools.capture_templates
```

按提示输入牌名（如 `1m`、`5p`、`E`）和槽位索引，将模板保存到 `templates/tiles/`。

### 4. 启动 AI 助手

```bash
python -m majsoul_ai
```

## 项目结构

```
maj/
├── config/default.yaml
├── majsoul_ai/
│   ├── main.py
│   ├── capture/window.py
│   ├── vision/
│   ├── game/
│   ├── ai/mortal.py
│   └── ui/overlay.py
├── tools/
└── templates/tiles/
```

## 工作原理

1. Win32 截取雀魂窗口
2. 画面配准到 1280×720 标准坐标
3. 模板匹配识别手牌
4. 增量构建 MJAI 事件流
5. Mortal 子进程返回最优策略
6. PyQt6 悬浮窗展示建议

## 已知限制

- 屏幕识别无法获取完整牌局信息，精度低于 MITM 方案（如 MahjongCopilot）
- 首次使用需手动采集牌面模板
- 仅支持 Windows 客户端

## 参考项目

- [Mortal](https://github.com/Equim-chan/Mortal)
- [MahjongCopilot](https://github.com/latorc/MahjongCopilot)
- [Akagi](https://github.com/shinkuan/Akagi)
- [cvmaj](https://github.com/xdedss/cvmaj)

## License

AGPL-3.0
