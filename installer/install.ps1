#Requires -Version 5.1
<#
.SYNOPSIS
  雀魂 AI 助手一键安装脚本（Windows）

.USAGE
  powershell -ExecutionPolicy Bypass -File installer\install.ps1
  或双击 installer\install.bat
#>
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\MajsoulAI",
    [string]$PythonVersion = "3.11",
    [switch]$SkipShortcuts
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    [!] $msg" -ForegroundColor Yellow }

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host @"

  ╔══════════════════════════════════════╗
  ║   雀魂 AI 助手 · 一键安装程序        ║
  ╚══════════════════════════════════════╝

"@ -ForegroundColor White

# --- 磁盘空间 ---
Write-Step "检查磁盘空间"
$drive = (Split-Path -Qualifier $InstallDir)
$freeGb = [math]::Round((Get-PSDrive ($drive.TrimEnd(':'))).Free / 1GB, 2)
Write-Ok "可用空间 ${freeGb} GB ($drive)"
if ($freeGb -lt 4) {
    Write-Warn "建议至少 4GB 空闲空间，继续可能失败"
}

# --- 安装目录 ---
Write-Step "准备安装目录: $InstallDir"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# 复制项目文件（排除 .git）
$exclude = @('.git', '.venv', 'venv', 'venv-mortal', '__pycache__', 'target', 'debug_capture.png')
Write-Step "复制程序文件"
Get-ChildItem $RepoRoot -Force | Where-Object {
    $_.Name -notin $exclude
} | ForEach-Object {
    $dest = Join-Path $InstallDir $_.Name
    if ($_.PSIsContainer) {
        Copy-Item $_.FullName $dest -Recurse -Force
    } else {
        Copy-Item $_.FullName $dest -Force
    }
}
Write-Ok "已复制到 $InstallDir"

# --- 查找 Python ---
Write-Step "查找 Python $PythonVersion"

function Find-Python {
    $candidates = @(
        "py -$PythonVersion",
        "python$PythonVersion",
        "python"
    )
    foreach ($cmd in $candidates) {
        try {
            $ver = Invoke-Expression "$cmd -c `"import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')`"" 2>$null
            if ($ver -eq $PythonVersion) { return $cmd }
        } catch {}
    }
    return $null
}

$pyCmd = Find-Python
if (-not $pyCmd) {
    Write-Warn "未找到 Python $PythonVersion，尝试从 python.org 下载安装器..."
    $pyInstaller = Join-Path $env:TEMP "python-$PythonVersion-installer.exe"
    $pyUrl = "https://www.python.org/ftp/python/$PythonVersion.9/python-$PythonVersion.9-amd64.exe"
    Write-Ok "下载 $pyUrl"
    try {
        Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing
        Start-Process -FilePath $pyInstaller -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $pyCmd = Find-Python
    } catch {
        Write-Host "    自动安装 Python 失败。请手动安装 Python $PythonVersion 后重新运行本脚本。" -ForegroundColor Red
        Write-Host "    下载: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
}
Write-Ok "使用 Python: $pyCmd"

# --- 创建虚拟环境 ---
Write-Step "创建虚拟环境"
$venvPath = Join-Path $InstallDir "venv"
if (Test-Path $venvPath) {
    Write-Warn "已存在 venv，跳过创建"
} else {
    Invoke-Expression "$pyCmd -m venv `"$venvPath`""
}
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"
Write-Ok $venvPath

# --- 安装依赖 ---
Write-Step "安装 Python 依赖（可能需要几分钟）"
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""

$pipMirrors = @(
    "https://mirrors.aliyun.com/pypi/simple/",
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://pypi.org/simple"
)
$reqFile = Join-Path $InstallDir "requirements.txt"
$installed = $false
foreach ($mirror in $pipMirrors) {
    $mirrorHost = ([uri]$mirror).Host
    Write-Ok "尝试 pip 源: $mirror"
    & $venvPip install -r $reqFile -i $mirror --trusted-host $mirrorHost 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) { $installed = $true; break }
}
if (-not $installed) {
    Write-Host "    pip 安装失败，请检查网络后重试" -ForegroundColor Red
    exit 1
}
Write-Ok "依赖安装完成"

# --- 生成配置 ---
Write-Step "生成配置文件"
$configPath = Join-Path $InstallDir "config\default.yaml"
$configContent = Get-Content $configPath -Raw -Encoding UTF8

# 写入 venv python 路径供参考（用户需自行配置 mortal）
$mortalPythonHint = ""
$mortalPaths = @(
    "$env:USERPROFILE\.conda\envs\mortal\python.exe",
    "C:\ProgramData\miniconda3\envs\mortal\python.exe",
    "C:\Mortal\venv-mortal\Scripts\python.exe"
)
foreach ($p in $mortalPaths) {
    if (Test-Path $p) {
        $mortalPythonHint = ($p -replace '\\', '/')
        break
    }
}

if ($mortalPythonHint) {
    $configContent = $configContent -replace 'python:\s*""', "python: `"$mortalPythonHint`""
    $configContent = $configContent -replace 'root:\s*""', 'root: "C:/Mortal"'
}
Set-Content -Path $configPath -Value $configContent -Encoding UTF8
Write-Ok $configPath

# --- 启动器脚本 ---
Write-Step "创建启动器"
$launcherPs1 = Join-Path $InstallDir "启动雀魂AI.ps1"
@'
# 雀魂 AI 助手启动器
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root "venv\Scripts\python.exe"
Set-Location $Root

function Show-Menu {
    Clear-Host
    Write-Host "  雀魂 AI 助手" -ForegroundColor Cyan
    Write-Host "  安装目录: $Root`n"
    Write-Host "  [1] 采集牌面模板（首次必做）"
    Write-Host "  [2] 启动 AI 助手"
    Write-Host "  [3] 调试截图 (test_capture)"
    Write-Host "  [4] 编辑配置 (default.yaml)"
    Write-Host "  [5] 打开模板目录"
    Write-Host "  [0] 退出`n"
}

do {
    Show-Menu
    $c = Read-Host "请选择"
    switch ($c) {
        "1" { & $Python -m tools.capture_templates; Read-Host "按回车继续" }
        "2" { & $Python -m majsoul_ai; Read-Host "按回车继续" }
        "3" { & $Python -m tools.test_capture; Read-Host "按回车继续" }
        "4" { notepad (Join-Path $Root "config\default.yaml"); Start-Sleep 1 }
        "5" { explorer (Join-Path $Root "templates\tiles") }
        "0" { break }
    }
} while ($c -ne "0")
'@ | Set-Content -Path $launcherPs1 -Encoding UTF8

$launcherBat = Join-Path $InstallDir "启动雀魂AI.bat"
"@echo off`r`ncd /d `"%~dp0`"`r`npowershell -ExecutionPolicy Bypass -File `"%~dp0启动雀魂AI.ps1`"`r`n" | Set-Content -Path $launcherBat -Encoding ASCII
Write-Ok $launcherBat

# --- 桌面快捷方式 ---
if (-not $SkipShortcuts) {
    Write-Step "创建桌面快捷方式"
    $wsh = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath("Desktop")
    $lnk = $wsh.CreateShortcut((Join-Path $desktop "雀魂AI助手.lnk"))
    $lnk.TargetPath = $launcherBat
    $lnk.WorkingDirectory = $InstallDir
    $lnk.Description = "雀魂麻将 AI 实时分析助手"
    $lnk.Save()
    Write-Ok "桌面快捷方式: 雀魂AI助手.lnk"
}

# --- 完成 ---
Write-Host @"

  ╔══════════════════════════════════════╗
  ║           安装完成！                   ║
  ╚══════════════════════════════════════╝

  安装目录: $InstallDir
  启动方式: 双击「启动雀魂AI.bat」或桌面快捷方式

  首次使用:
    1. 打开雀魂并进入对局
    2. 启动器选 [1] 采集牌面模板（37/37）
    3. 配置 Mortal（可选）: 编辑 config\default.yaml
    4. 启动器选 [2] 启动 AI 助手

  Mortal AI 需单独安装，见 docs\DEPLOY.md

"@ -ForegroundColor Green

$open = Read-Host "是否现在打开启动器? (Y/n)"
if ($open -ne "n" -and $open -ne "N") {
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$launcherPs1`""
}
