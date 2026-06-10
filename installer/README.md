# 一键安装 / 打包说明

## 用户：一键安装（推荐）

1. 克隆或解压本项目到任意目录
2. **双击** `installer\install.bat`  
   或在 PowerShell 中：

```powershell
cd C:\maj
powershell -ExecutionPolicy Bypass -File installer\install.ps1
```

3. 安装完成后：
   - 默认目录：`%LOCALAPPDATA%\MajsoulAI`
   - 双击 **「启动雀魂AI.bat」** 或桌面快捷方式

### 安装脚本会自动完成

- 复制程序到安装目录
- 创建 Python 虚拟环境 `venv`
- 从国内 pip 镜像安装依赖
- 生成启动菜单（采集模板 / 启动助手 / 调试）
- 创建桌面快捷方式

### 仍需手动完成（无法完全打包）

| 项目 | 原因 |
|------|------|
| **Mortal + libriichi** | 需 Rust 编译，体积大，模型有版权 |
| **mortal.pth 权重** | 需自行获取 |
| **牌面模板** | 需在对局中采集（启动器 [1]） |

Mortal 配置见 [docs/DEPLOY.md](../docs/DEPLOY.md)。

### 自定义安装路径

```powershell
powershell -ExecutionPolicy Bypass -File installer\install.ps1 -InstallDir "D:\MajsoulAI"
```

### 卸载

```powershell
powershell -ExecutionPolicy Bypass -File installer\uninstall.ps1
```

---

## 开发者：打包便携 exe（可选）

```powershell
# 先 install.ps1 创建 venv
powershell -ExecutionPolicy Bypass -File installer\install.ps1
powershell -ExecutionPolicy Bypass -File installer\build_portable.ps1
```

输出：`dist\MajsoulAI-Portable\MajsoulAI.exe`

> 便携版体积较大（含 OpenCV/PyQt6），且仍不包含 Mortal。
