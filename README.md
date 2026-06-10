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
- （推荐）[Mortal](https://github.com/Equim-chan/Mortal) 及模型权重 `mortal.pth`

> **完整部署指南**（Miniconda + Rust/MSYS2 + PyTorch + Mortal + 本项目）：  
> 见 **[docs/DEPLOY.md](docs/DEPLOY.md)**

## 一键安装（Windows 推荐）

双击 **`installer\install.bat`**，或：

```powershell
powershell -ExecutionPolicy Bypass -File installer\install.ps1
```

自动完成：复制文件 → 创建 venv → 安装依赖 → 桌面快捷方式 → 启动菜单。  
详见 **[installer/README.md](installer/README.md)**。

> Mortal AI 与牌面模板仍需按向导单独配置。

## 快速开始（手动）

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

### 3. 采集牌面模板（图形化）

```bash
python -m tools.capture_templates
```

打开图形窗口：左侧显示 37 种牌的采集进度（绿色=已采集），右侧实时显示手牌槽位。  
操作：① 点击缺失的牌名 ② 点击对应手牌槽位完成采集。

### 4. 运行时牌面监视

启动 `python -m majsoul_ai` 后会同时出现两个悬浮窗：
- **AI 建议窗**：推荐出牌
- **牌面监视窗**：实时显示手牌、牌河、副露、宝牌，便于与游戏画面对照

可在 `config/default.yaml` 的 `overlay.show_recognition_panel` 关闭监视窗。

### 5. 启动 AI 助手

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
3. 模板匹配识别手牌、**四家牌河**、**副露**
4. **MjaiRebuilder** 从完整快照重建 MJAI 事件流（按回合交织牌河，插入副露）
5. Mortal 子进程返回最优策略
6. PyQt6 悬浮窗展示建议

### MJAI 重建逻辑

- 从 `GameSnapshot`（手牌 + 牌河 + 副露 + 场况）完整重建事件序列
- 按 `oya` 起始的回合顺序交织四家牌河中的出牌
- 在对应玩家首次出牌前插入 chi/pon/kan 事件
- 轮到自己且手牌 14 张时，末尾追加 `tsumo` 触发 AI 决策

## 调试

```bash
# 保存标注截图（手牌 + 牌河 + 副露 + MJAI 事件统计）
python -m tools.test_capture

# 单元测试
python tests/test_mjai_rebuilder.py
```

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
