# Install the prd-to-xmind skill into a WorkBuddy skills directory.
# Usage: .\install.ps1 [-Dest "$env:USERPROFILE\.workbuddy-ai\skills"]

param(
  [string]$Dest = "$env:USERPROFILE\.workbuddy-ai\skills"
)

$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "skills\prd-to-xmind-testcases"
$target = Join-Path $Dest "prd-to-xmind-testcases"

if (-not (Test-Path $src)) {
  Write-Error "找不到 $src，请在仓库根目录执行本脚本"
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
if (Test-Path $target) {
  Write-Host "已存在 $target，将覆盖同名技能目录"
  Remove-Item $target -Recurse -Force
}
Copy-Item $src $target -Recurse -Force

Write-Host "✅ 已安装到 $target"
Write-Host "   重启会话后技能才会出现在可用列表里"
