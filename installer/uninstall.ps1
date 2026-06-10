#Requires -Version 5.1
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\MajsoulAI"
)

Write-Host "将删除安装目录: $InstallDir" -ForegroundColor Yellow
$confirm = Read-Host "确认卸载? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") { exit 0 }

if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force
    Write-Host "已删除 $InstallDir" -ForegroundColor Green
}

$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "雀魂AI助手.lnk"
if (Test-Path $lnk) {
    Remove-Item $lnk -Force
    Write-Host "已删除桌面快捷方式" -ForegroundColor Green
}

Write-Host "卸载完成。Mortal / conda 环境需手动删除。" -ForegroundColor Cyan
