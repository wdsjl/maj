#Requires -Version 5.1
<#
  打包便携版（单目录，含嵌入式 Python 依赖）
  需在已安装依赖的 venv 中运行，或先执行 install.ps1

  用法:
    powershell -ExecutionPolicy Bypass -File installer\build_portable.ps1
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$OutDir = Join-Path $RepoRoot "dist\MajsoulAI-Portable"

Write-Host "构建便携版 -> $OutDir" -ForegroundColor Cyan

$venvPython = Join-Path $RepoRoot "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = Join-Path $env:LOCALAPPDATA "MajsoulAI\venv\Scripts\python.exe"
}
if (-not (Test-Path $venvPython)) {
    Write-Host "请先运行 installer\install.ps1 创建 venv" -ForegroundColor Red
    exit 1
}

& $venvPython -m pip install pyinstaller -q -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir | Out-Null

# PyInstaller 打包启动器（模板采集 + 主程序通过子进程调用较复杂，这里打包主入口菜单）
$spec = @"
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
root = Path(SPECPATH).parent.parent

a = Analysis(
    [str(root / 'installer' / 'launcher_entry.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'config'), 'config'),
        (str(root / 'templates'), 'templates'),
        (str(root / 'majsoul_ai'), 'majsoul_ai'),
        (str(root / 'tools'), 'tools'),
    ],
    hiddenimports=['majsoul_ai', 'cv2', 'PyQt6', 'yaml', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    [], name='MajsoulAI', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=True, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None,
)
"@
$specPath = Join-Path $RepoRoot "installer\MajsoulAI.spec"
Set-Content $specPath $spec -Encoding UTF8

Push-Location $RepoRoot
& $venvPython -m PyInstaller --clean --distpath $OutDir --workpath (Join-Path $RepoRoot "build") $specPath
Pop-Location

Copy-Item (Join-Path $RepoRoot "installer\install.ps1") $OutDir
Copy-Item (Join-Path $RepoRoot "docs\DEPLOY.md") $OutDir
Write-Host "完成: $OutDir\MajsoulAI.exe" -ForegroundColor Green
