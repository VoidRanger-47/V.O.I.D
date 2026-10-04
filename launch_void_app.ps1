# launch_void_app.ps1
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "      V.O.I.D. Advanced Neural Interface" -ForegroundColor Cyan
Write-Host "          Launching Native Desktop App..." -ForegroundColor DarkGray
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

python desktop_app.py

