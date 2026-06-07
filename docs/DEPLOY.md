# 雀魂 AI 助手 · Windows 完整部署指南

本文档从零开始，在 **Windows 10/11** 上部署整套环境：

```
Miniconda → Rust (MSYS2) → PyTorch → Mortal → 本项目 → 牌面模板 → 运行
```

预计涉及两个 Conda 环境：

| 环境名 | 用途 | Python 版本 |
|--------|------|-------------|
| `mortal` | Mortal AI 推理引擎 | 3.12（Mortal 官方） |
| `maj` | 雀魂助手（窗口捕捉 + 悬浮窗） | 3.10+ |

---

## 目录

1. [硬件与系统要求](#1-硬件与系统要求)
2. [安装 Miniconda](#2-安装-miniconda)
3. [安装 MSYS2 与 Rust](#3-安装-msys2-与-rust)
4. [编译安装 Mortal](#4-编译安装-mortal)
5. [安装 PyTorch](#5-安装-pytorch)
6. [获取 Mortal 模型权重](#6-获取-mortal-模型权重)
7. [配置 Mortal](#7-配置-mortal)
8. [部署本项目](#8-部署本项目)
9. [采集牌面模板](#9-采集牌面模板)
10. [启动与验证](#10-启动与验证)
11. [常见问题](#11-常见问题)
12. [附录：目录结构速查](#12-附录目录结构速查)

---

## 1. 硬件与系统要求

### 操作系统
- Windows 10 或 Windows 11（64 位）
- 雀魂 **Windows 客户端**（非浏览器版；窗口捕捉依赖 Win32 API）

### 硬件
| 组件 | 最低 | 推荐 |
|------|------|------|
| CPU | 4 核 | 8 核及以上 |
| 内存 | 8 GB | 16 GB |
| 磁盘 | 10 GB 可用 | SSD，20 GB+ |
| 显卡 | 无（CPU 推理） | NVIDIA GPU + CUDA（推理更快） |

### 网络
- 能访问 GitHub、PyPI、conda-forge
- 克隆仓库、下载 PyTorch / 模型权重需要稳定网络

---

## 2. 安装 Miniconda

Miniconda 用于管理 Python 环境，比完整 Anaconda 更轻量。二者任选其一即可。

### 2.1 下载安装

1. 打开 [Miniconda 官网](https://docs.conda.io/en/latest/miniconda.html)
2. 下载 **Windows 64-bit** 安装包（`.exe`）
3. 安装时建议勾选：
   - ✅ *Add Miniconda3 to my PATH environment variable*（方便命令行使用；若不勾选，请用「Anaconda Prompt」）
   - ✅ *Register Miniconda3 as my default Python*

### 2.2 验证

打开 **PowerShell** 或 **Anaconda Prompt**：

```powershell
conda --version
# 应输出 conda 23.x 或更高
```

### 2.3 初始化（可选）

```powershell
conda init powershell
# 重启 PowerShell 后提示符前会出现 (base)
```

---

## 3. 安装 MSYS2 与 Rust

Mortal 的 `libriichi` 核心由 **Rust** 编写，Windows 上需通过 **MSYS2** 工具链编译。

### 3.1 安装 MSYS2

1. 打开 [MSYS2 官网](https://www.msys2.org/)
2. 下载并运行安装程序，默认安装到 `C:\msys64`
3. 安装完成后，打开 **「MSYS2 UCRT64」** 终端（开始菜单中搜索）

### 3.2 更新并安装编译工具

在 **MSYS2 UCRT64** 终端中执行：

```bash
pacman -Syu
# 若提示关闭窗口，关闭后重新打开 UCRT64，再执行：
pacman -Su

pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain git
```

### 3.3 安装 Rust

仍在 **MSYS2 UCRT64** 终端：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# 安装选项直接回车（默认 stable）
source $HOME/.cargo/env
rustc --version
cargo --version
```

应看到类似 `rustc 1.8x.x` 的输出。

### 3.4 安装 Git（若系统尚未安装）

Windows 上克隆仓库还需要 [Git for Windows](https://git-scm.com/download/win)。MSYS2 内已有 git，PowerShell 中建议也装一份。

---

## 4. 编译安装 Mortal

### 4.1 克隆 Mortal 仓库

在 **PowerShell** 或 **MSYS2 UCRT64** 中：

```powershell
cd C:\
git clone https://github.com/Equim-chan/Mortal.git
cd Mortal
```

以下记 `C:\Mortal` 为 **MORTAL_ROOT**。

### 4.2 创建 Mortal 的 Conda 环境

在 **PowerShell（Anaconda Prompt）** 中：

```powershell
cd C:\Mortal
conda env create -f environment.yml
conda activate mortal
```

这会创建名为 `mortal` 的环境，Python 版本为 **3.12**。

### 4.3 安装 PyTorch

见 [第 5 节](#5-安装-pytorch)，在 `mortal` 环境中执行。

### 4.4 编译 libriichi

在 **MSYS2 UCRT64** 终端中（注意路径格式）：

```bash
cd /c/Mortal
source $HOME/.cargo/env
cargo build -p libriichi --lib --release
```

首次编译约 5～15 分钟。成功后执行：

```bash
cp target/release/riichi.dll mortal/libriichi.pyd
```

> **说明**：Windows 产物名为 `riichi.dll`，复制并重命名为 `libriichi.pyd` 供 Python 导入。

### 4.5 验证 libriichi

回到 **PowerShell**，激活 mortal 环境：

```powershell
conda activate mortal
cd C:\Mortal\mortal
python -c "import libriichi; print('libriichi OK')"
```

输出 `libriichi OK` 即表示编译成功。

---

## 5. 安装 PyTorch

在 **`conda activate mortal`** 后的 PowerShell 中安装。

### 5.1 CPU 版（无 NVIDIA 显卡）

```powershell
pip install torch
```

### 5.2 CUDA 版（有 NVIDIA 显卡，推荐）

1. 查看显卡驱动支持的 CUDA 版本（[PyTorch 官网](https://pytorch.org/get-started/locally/)）
2. 按官网命令安装，例如 CUDA 12.1：

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### 5.3 验证 PyTorch

```powershell
python -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

- CPU 版：`CUDA: False` 正常
- GPU 版：`CUDA: True` 表示可用显卡加速

---

## 6. 获取 Mortal 模型权重

Mortal 推理需要预训练权重，常见文件：

| 文件 | 说明 |
|------|------|
| `mortal.pth` | 主模型（必需） |
| `grp.pth` | GRP 辅助模型（config 中若启用则需要） |

### 获取途径

1. [Mortal 官方说明](https://gist.github.com/Equim-chan/cf3f01735d5d98f1e7be02e94b288c56)
2. [Akagi 项目](https://github.com/shinkuan/Akagi) / 其 Discord 社区提供的四麻兼容模型
3. 自行训练（进阶，见 Mortal 文档）

### 放置位置

将权重文件放到：

```
C:\Mortal\mortal\mortal.pth
C:\Mortal\mortal\grp.pth      # 若有
```

---

## 7. 配置 Mortal

### 7.1 创建 config.toml

在 `C:\Mortal\mortal\` 下创建 `config.toml`（可参考仓库中的 example）：

```toml
[control]
version = 4
state_file = "mortal.pth"
device = "cpu"          # 有 NVIDIA 显卡且装了 CUDA 版 PyTorch 时改为 "cuda:0"
batch_size = 512

[grp]
state_file = "grp.pth"  # 若没有 grp.pth，可注释掉整个 [grp] 段并查阅 Mortal 版本说明
```

> 权重路径相对于 `mortal/` 工作目录，通常只写文件名即可。

### 7.2 测试 Mortal 能否启动

```powershell
conda activate mortal
cd C:\Mortal\mortal
python mortal.py 0
```

- 进程挂起、无报错：正常（按 `Ctrl+C` 退出）
- 若报 `FileNotFoundError: mortal.pth`：检查权重是否放对位置
- 若报 `ImportError: libriichi`：检查 `libriichi.pyd` 是否在 `mortal/` 目录

---

## 8. 部署本项目

### 8.1 克隆项目

```powershell
cd C:\
git clone https://github.com/wdsjl/maj.git
cd maj
```

若你已在其他路径 clone，进入对应目录即可。

### 8.2 创建本项目的 Conda 环境

```powershell
conda create -n maj python=3.11 -y
conda activate maj
pip install -r requirements.txt
```

依赖包括：OpenCV、PyQt6、pywin32（Windows 窗口捕捉）等。

### 8.3 配置 config/default.yaml

编辑 `config/default.yaml` 中的 **mortal** 与 **game** 段：

```yaml
mortal:
  # Mortal 仓库根目录（含 mortal/mortal.py 的上一级）
  root: "C:/Mortal"

  # 留空即可；权重在 Mortal 的 config.toml 中配置
  model_path: ""

  # 指向 mortal 环境的 Python（重要！）
  python: "C:/Users/你的用户名/miniconda3/envs/mortal/python.exe"

  player_id: 0
  fallback_bot: true

game:
  seat: 0        # 与 player_id 保持一致（自家在屏幕下方）
  oya: 0         # 亲家 MJAI id，暂可手动设置
  bakaze: "E"
  kyoku: 1
```

**查找 Python 路径**：

```powershell
conda activate mortal
where python
# 复制输出的完整路径，将反斜杠改为正斜杠写入 yaml
```

### 8.4 配置说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `mortal.root` | ✅ | Mortal 根目录，如 `C:/Mortal` |
| `mortal.python` | ✅ 强烈推荐 | `mortal` 环境的 python.exe，否则可能找不到 libriichi |
| `mortal.player_id` | ✅ | 你的座位 0～3 |
| `game.seat` | ✅ | 与 `player_id` 相同 |
| `mortal.fallback_bot` | 可选 | Mortal 不可用时是否用简易 bot |

---

## 9. 采集牌面模板

模板用于屏幕识别，**每种牌至少一张**，共 34 种常规牌（赤宝牌可选）。

### 9.1 启动雀魂

打开雀魂 Windows 客户端，进入任意对局（练习场即可）。

### 9.2 运行采集工具

```powershell
conda activate maj
cd C:\maj
python -m tools.capture_templates
```

### 9.3 操作说明

```
> list          # 查看还缺哪些牌
> 1m            # 输入牌名，再选槽位 0-13 采集
> slot 3        # 直接指定槽位采集
> q             # 退出
```

牌名对照：

| 类型 | 示例 |
|------|------|
| 万 | `1m`～`9m` |
| 筒 | `1p`～`9p` |
| 索 | `1s`～`9s` |
| 字 | `E`东 `S`南 `W`西 `N`北 `P`白 `F`发 `C`中 |
| 赤 | `5mr` `5pr` `5sr`（可选） |

**不必一局收齐**：多打几局，遇到新手牌就采一次，模板会累积在 `templates/tiles/`。

建议进度：`已有模板: 34/37` 再正式使用 AI 助手。

---

## 10. 启动与验证

### 10.1 调试截图（可选）

```powershell
conda activate maj
cd C:\maj
python -m tools.test_capture
# 生成 debug_capture.png，检查手牌/牌河区域是否对齐
```

若区域框不准，微调 `config/default.yaml` 中 `vision.hand` / `vision.rivers` 坐标。

### 10.2 启动 AI 助手

1. 打开雀魂并进入对局
2. 运行：

```powershell
conda activate maj
cd C:\maj
python -m majsoul_ai
```

或指定配置：

```powershell
python -m majsoul_ai --mortal-root "C:/Mortal" --player-id 0
```

### 10.3 成功标志

| 现象 | 含义 |
|------|------|
| 日志出现 `Mortal 进程已启动 (player_id=0)` | Mortal 接入成功 |
| 悬浮窗推荐前显示 ✅（非「简易模式」） | 正在使用 Mortal 推理 |
| 悬浮窗显示「简易模式」 | Mortal 未加载，检查第 11 节 |
| 状态栏 `手牌 14 \| 牌河 P0:2 ...` | 牌河识别工作中 |

---

## 11. 常见问题

### Q1：`import libriichi` 失败

- 确认 `C:\Mortal\mortal\libriichi.pyd` 存在
- 确认在 **mortal** 环境中测试
- 重新编译：`cargo build -p libriichi --lib --release` 并复制 dll

### Q2：Mortal 启动报找不到 `mortal.pth`

- 权重放在 `C:\Mortal\mortal\mortal.pth`
- `config.toml` 中 `state_file = "mortal.pth"`

### Q3：悬浮窗一直是「简易模式」

1. `config/default.yaml` 中 `mortal.root` 是否正确
2. `mortal.python` 是否指向 **mortal** 环境的 python
3. 手动测试：
   ```powershell
   C:\Users\...\envs\mortal\python.exe C:\Mortal\mortal\mortal.py 0
   ```

### Q4：`cargo build` 在 PowerShell 里找不到

Rust 编译必须在 **MSYS2 UCRT64** 终端进行，不要用普通 PowerShell。

### Q5：牌识别全是 `?`

- 运行 `python -m tools.capture_templates`，用 `list` 查看缺失模板
- 调低 `vision.match_threshold`（如 `0.70`）可能有帮助，但过低易误识别

### Q6：牌河/手牌区域框不准

- 运行 `python -m tools.test_capture` 查看 `debug_capture.png`
- 雀魂窗口需完整可见，不要被遮挡
- 尝试固定窗口大小或使用默认分辨率

### Q7：CPU 推理太慢

- 安装 CUDA 版 PyTorch
- Mortal `config.toml` 中 `device = "cuda:0"`
- 降低 `window.capture_fps`（如 `3`）减少调用频率

### Q8：两个 Conda 环境搞混

```powershell
conda activate maj      # 运行 python -m majsoul_ai
conda activate mortal   # 仅测试 Mortal 或编译时使用
```

---

## 12. 附录：目录结构速查

```
C:\
├── Mortal\                          # mortal.root
│   ├── mortal\
│   │   ├── mortal.py
│   │   ├── config.toml              # Mortal 配置
│   │   ├── mortal.pth               # 模型权重
│   │   ├── grp.pth                  # 可选
│   │   └── libriichi.pyd            # 编译产物
│   └── target\release\riichi.dll    # 编译原始输出
│
└── maj\                             # 本项目
    ├── config\default.yaml          # 助手配置
    ├── templates\tiles\             # 牌面模板 *.png
    ├── majsoul_ai\                  # 主程序
    └── tools\                       # 采集/调试工具
```

### 一键检查脚本（PowerShell）

```powershell
Write-Host "=== 环境检查 ===" -ForegroundColor Cyan

conda run -n mortal python -c "import libriichi, torch; print('Mortal env: libriichi + torch OK')"
conda run -n maj python -c "import cv2, PyQt6; print('Maj env: cv2 + PyQt6 OK')"

Test-Path C:\Mortal\mortal\mortal.py
Test-Path C:\Mortal\mortal\libriichi.pyd
Test-Path C:\Mortal\mortal\mortal.pth

Write-Host "模板数量:" (Get-ChildItem C:\maj\templates\tiles\*.png -ErrorAction SilentlyContinue).Count
```

---

## 参考链接

- [Mortal 官方文档](https://mortal.ekyu.moe/)
- [Mortal GitHub](https://github.com/Equim-chan/Mortal)
- [Mortal 编译说明](https://mortal.ekyu.moe/user/build.html)
- [PyTorch 安装](https://pytorch.org/get-started/locally/)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- [MSYS2](https://www.msys2.org/)
- [Rustup](https://rustup.rs/)

---

**部署完成后推荐顺序**：采集模板 → `test_capture` 校准区域 → 启动 `majsoul_ai` → 练习场试一局。
