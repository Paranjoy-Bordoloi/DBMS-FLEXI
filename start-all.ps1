param(
    [switch]$SkipTomcat
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$frontendDir = Join-Path $repoRoot 'frontend'

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found at $pythonExe"
}

if (-not (Test-Path $frontendDir)) {
    Write-Error "Frontend directory not found at $frontendDir"
}

Write-Output 'Starting backend (FastAPI)...'
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$repoRoot'; & '$pythonExe' -m uvicorn backend.app.main:app --reload"
)

Write-Output 'Starting frontend (Vite)...'
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$frontendDir'; npm run dev"
)

if (-not $SkipTomcat) {
    $tomcatBinDir = "D:\apache-tomcat-11.0.18\bin"
    $tomcatStartup = Join-Path $tomcatBinDir "startup.bat"

    if (Test-Path $tomcatStartup) {
        Write-Output "Starting Tomcat..."
        
        Start-Process cmd.exe -ArgumentList "/k", "cd /d `"$tomcatBinDir`" && startup.bat"
    } else {
        Write-Warning "Tomcat startup script not found."
    }
}

Write-Output ''
Write-Output 'Startup commands launched in new terminals.'
Write-Output 'FastAPI expected at: http://127.0.0.1:8000'
Write-Output 'Frontend expected at: http://localhost:5173 (or next free port)'
Write-Output 'Admin expected at: http://localhost:8080/admin/health'