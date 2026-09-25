#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Explicitly starts nanoCAD BIM Строительство 26.0 (СПДС profile) for MCP.
.DESCRIPTION
    This script is never called by MCP startup. The MCP server only connects
    to an already running nanoCAD instance.
#>
param(
    [switch]$NoWait,
    [switch]$NoInstall,
    [string]$PluginPath = "",
    [string]$NanoCadExe = 'C:\Program Files\Nanosoft\nanoCAD BIM Строительство x64 26.0\BIMSP.exe'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$iniPath = 'C:\Program Files\Nanosoft\nanoCAD x64 26.0\nCad.ini'

if (-not (Test-Path -LiteralPath $NanoCadExe)) {
    throw "nanoCAD BIM Строительство не найден: $NanoCadExe"
}
if (-not $PluginPath) {
    $PluginPath = Join-Path $repoRoot 'engine\dist\CadEngine.Plugin.dll'
}
if (-not (Test-Path -LiteralPath $PluginPath)) {
    throw "MCP DLL не найдена: $PluginPath"
}
if (-not (Test-Path -LiteralPath $iniPath)) {
    throw "nCad.ini не найден: $iniPath"
}

$content = [IO.File]::ReadAllText($iniPath, [Text.Encoding]::UTF8)
if (-not $content.Contains($PluginPath)) {
    if ($NoInstall) {
        throw "MCP DLL не прописана в nCad.ini: $PluginPath"
    }
    $marker = "[\NetModules]`r`n"
    if (-not $content.Contains($marker)) {
        throw 'Секция [\NetModules] отсутствует в nCad.ini'
    }
    $content = $content.Replace($marker, $marker + $PluginPath + "`r`n")
    try {
        [IO.File]::WriteAllText($iniPath, $content, (New-Object Text.UTF8Encoding($true)))
    } catch [System.UnauthorizedAccessException] {
        throw 'Нет прав на nCad.ini. Запустите сценарий от имени администратора.'
    }
}

if (Get-Process -Name 'BIMSP' -ErrorAction SilentlyContinue) {
    Write-Host 'nanoCAD BIM Строительство уже запущен.'
} else {
    Start-Process -FilePath $NanoCadExe -WorkingDirectory (Split-Path $NanoCadExe -Parent)
    Write-Host 'Запущен nanoCAD BIM Строительство 26.0 (СПДС 26.0).'
}

if (-not $NoWait) {
    $deadline = (Get-Date).AddSeconds(90)
    do {
        try {
            $health = Invoke-RestMethod 'http://localhost:5080/api/system/health' -TimeoutSec 2
            if ($health.status -eq 'ok') {
                Write-Host 'MCP DLL загружена, API доступен.'
                exit 0
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)
    throw 'nanoCAD запущен, но MCP API на порту 5080 не ответил за 90 секунд.'
}