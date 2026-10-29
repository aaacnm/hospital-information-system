param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Start', 'Stop')]
    [string]$Action,
    [string]$DataPath,
    [string]$PythonPath,
    [string]$NodePath,
    [int]$Port = 8000,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$projectRoot = [IO.Path]::GetFullPath($PSScriptRoot)
if (-not $DataPath) {
    $DataPath = Join-Path $projectRoot 'demo-data'
}
$DataPath = [IO.Path]::GetFullPath($DataPath)
$statePath = Join-Path $DataPath 'running.json'

function Read-RunState {
    if (Test-Path -LiteralPath $statePath) {
        $stream = [IO.File]::Open($statePath, 'Open', 'Read', ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
        $reader = New-Object IO.StreamReader($stream, [Text.Encoding]::UTF8)
        try { $text = $reader.ReadToEnd() } finally { $reader.Dispose() }
        return $text | ConvertFrom-Json
    }
    return $null
}

function Get-OwnedProcesses($state) {
    if (-not $state -or $state.project_root -ne $projectRoot -or -not $state.instance_id) { return }
    foreach ($processId in @($state.pid, $state.parent_pid) | Select-Object -Unique) {
        $item = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$processId)" -ErrorAction SilentlyContinue
        if ($item -and $item.CommandLine -match '-m\s+scripts\.demo_server\b' -and $item.CommandLine -match [regex]::Escape([string]$state.instance_id)) {
            $item
        }
    }
}

function Test-Ready($state) {
    $owners = @(Get-OwnedProcesses $state)
    if (-not ($owners | Where-Object { $_.ProcessId -eq $state.pid })) { return $false }
    $listener = Get-NetTCPConnection -LocalPort ([int]$state.port) -State Listen -ErrorAction SilentlyContinue
    if (-not ($listener | Where-Object { $_.OwningProcess -eq $state.pid -and $_.LocalAddress -eq '127.0.0.1' })) { return $false }
    try {
        $health = Invoke-RestMethod -Uri ($state.url + '/health') -TimeoutSec 2 -UseBasicParsing
        return $health.status -eq 'ok' -and $health.service -eq 'hospital-information-system-api'
    } catch {
        return $false
    }
}

function Show-Ready($state) {
    Write-Host ''
    Write-Host '和序 HIS 已启动！' -ForegroundColor Green
    Write-Host ('演示网页：' + $state.url)
    Write-Host '登录页可直接选择演示身份，统一密码：Demo123!'
    Write-Host '演示结束后，双击“关闭系统.cmd”。这个窗口现在可以关闭。'
    if (-not $NoBrowser) {
        try { Start-Process -FilePath ([string]$state.url) } catch {
            Write-Host ('系统已启动，浏览器未能自动打开。请在浏览器输入：' + $state.url) -ForegroundColor Yellow
        }
    }
}

function Find-BasePython {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($version in @('-3.12', '-3.11', '-3')) {
            try {
                $candidate = & $launcher.Source $version -c 'import sys; print(sys.executable)' 2>$null
                if ($LASTEXITCODE -eq 0 -and $candidate) { return [string]$candidate }
            } catch { continue }
        }
    }
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') { return $command.Source }
    throw '请先安装 Python 3.12，并在安装时勾选 Add python.exe to PATH，再双击启动。'
}

function Prepare-Python($state) {
    $target = $PythonPath
    if (-not $target -and $state -and $state.project_root -eq $projectRoot -and $state.python_path) {
        if (Test-Path -LiteralPath $state.python_path) { $target = [string]$state.python_path }
    }
    $environment = Join-Path $projectRoot '.venv'
    if (-not $target) { $target = Join-Path $environment 'Scripts\python.exe' }
    if (-not (Test-Path -LiteralPath $target)) {
        if ($PythonPath) { throw ('指定的 Python 不存在：' + $PythonPath) }
        $base = Find-BasePython
        & $base -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
        if ($LASTEXITCODE -ne 0) { throw '需要 Python 3.11 或更新版本，建议安装 Python 3.12。' }
        Write-Host '首次启动：正在创建本项目的 Python 环境……'
        & $base -m venv $environment | Out-Host
        if ($LASTEXITCODE -ne 0) { throw '创建项目环境失败，请检查文件夹是否可写。' }
    }
    & $target -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
    if ($LASTEXITCODE -ne 0) { throw '需要 Python 3.11 或更新版本，建议安装 Python 3.12。' }
    $requirements = Join-Path $projectRoot 'backend\requirements.txt'
    $check = @'
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
try:
    matches = all(version(line.split('==')[0].split('[')[0]) == line.split('==')[1] for line in Path(sys.argv[1]).read_text().splitlines() if line and not line.startswith('#'))
except PackageNotFoundError:
    matches = False
sys.exit(0 if matches else 1)
'@
    & $target -c $check $requirements
    if ($LASTEXITCODE -ne 0) {
        & $target -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)'
        if ($LASTEXITCODE -ne 0) { throw '依赖只能安装到项目独立环境，请不要把系统 Python 作为项目环境传入。' }
        Write-Host '首次启动或依赖已更新：正在准备项目依赖，需要联网……'
        & $target -m pip install --disable-pip-version-check -r $requirements | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Python 依赖准备失败，请检查网络，之后重新双击启动。' }
    }
    return $target
}

function Prepare-Web {
    $node = $NodePath
    if (-not $node) {
        $command = Get-Command node.exe -ErrorAction SilentlyContinue
        if ($command) { $node = $command.Source }
    }
    if (-not $node -or -not (Test-Path -LiteralPath $node)) { throw '请先安装 Node.js 22.12 或更新的 LTS 版本，再双击启动。' }
    $nodeVersion = & $node -p 'process.versions.node'
    if ($LASTEXITCODE -ne 0) { throw '无法运行 Node.js，请重新检查安装。' }
    $parts = $nodeVersion.Split('.')
    if (-not (([int]$parts[0] -eq 20 -and [int]$parts[1] -ge 19) -or ([int]$parts[0] -eq 22 -and [int]$parts[1] -ge 12) -or [int]$parts[0] -gt 22)) {
        throw 'Node.js 版本过旧，请安装 22.12 或更新的 LTS 版本。'
    }
    $npm = Join-Path (Split-Path -Parent $node) 'node_modules\npm\bin\npm-cli.js'
    if (-not (Test-Path -LiteralPath $npm)) { throw '没有找到 npm，请使用包含 npm 的 Node.js 官方安装。' }
    $frontend = Join-Path $projectRoot 'frontend'
    $check = @'
const fs = require('node:fs');
const path = require('node:path');
const root = process.argv[1];
const expected = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'))).packages;
const installedPath = path.join(root, 'node_modules/.package-lock.json');
if (!fs.existsSync(installedPath)) process.exit(1);
const installed = JSON.parse(fs.readFileSync(installedPath)).packages;
const matches = Object.entries(expected).every(([name, item]) => !name || (!installed[name] && item.optional) || (installed[name] && installed[name].version === item.version && installed[name].integrity === item.integrity && fs.existsSync(path.join(root, name))));
process.exit(matches ? 0 : 1);
'@
    & $node -e $check $frontend
    $installNeeded = $LASTEXITCODE -ne 0
    if ($installNeeded) {
        Write-Host '首次启动或依赖已更新：正在准备网页依赖，需要联网……'
        & $node $npm ci --prefix $frontend | Out-Host
        if ($LASTEXITCODE -ne 0) { throw '网页依赖准备失败，请检查网络，之后重新双击启动。' }
    }
    $web = Join-Path $frontend 'dist'
    $index = Join-Path $web 'index.html'
    $inputs = @(Get-ChildItem -LiteralPath $frontend -File | Where-Object { $_.Name -match '^(package(-lock)?\.json|index\.html|vite\.config\.ts|tsconfig.*\.json)$' })
    foreach ($directory in @('src', 'public')) {
        $inputPath = Join-Path $frontend $directory
        if (Test-Path -LiteralPath $inputPath) { $inputs += @(Get-ChildItem -LiteralPath $inputPath -Recurse -File) }
    }
    $latest = $inputs | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($installNeeded -or -not (Test-Path -LiteralPath $index) -or $latest.LastWriteTimeUtc -gt (Get-Item -LiteralPath $index).LastWriteTimeUtc) {
        Write-Host '正在生成演示网页，完成后会自动打开……'
        $env:VITE_API_BASE_URL = '/api'
        & $node $npm run build --prefix $frontend | Out-Host
        if ($LASTEXITCODE -ne 0) { throw '网页构建失败，请把窗口提示发给组员。' }
    }
    return $web
}

function Stop-Demo {
    $state = Read-RunState
    if (@(Get-OwnedProcesses $state).Count -eq 0) {
        Write-Host '当前目录的演示系统没有运行，无需重复关闭。' -ForegroundColor Green
        return
    }
    Write-Host '正在保存并关闭演示系统，请稍等……'
    $signal = Join-Path $DataPath ('stop-' + $state.instance_id + '.signal')
    [IO.File]::WriteAllText($signal, 'stop')
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 250
        if (@(Get-OwnedProcesses $state).Count -eq 0) {
            $remaining = Get-NetTCPConnection -LocalPort ([int]$state.port) -State Listen -ErrorAction SilentlyContinue |
                Where-Object { $_.OwningProcess -eq $state.pid }
            if (-not $remaining) {
                Write-Host '系统已关闭，演示数据已保留。浏览器中的页面可以直接关闭。' -ForegroundColor Green
                return
            }
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw ('关闭超时，请把此提示和日志目录发给组员：' + (Join-Path $DataPath 'logs'))
}

function Start-Demo {
    if (-not (Test-Path -LiteralPath $DataPath)) { New-Item -ItemType Directory -Path $DataPath | Out-Null }
    try {
        $startLock = [IO.File]::Open((Join-Path $DataPath 'launcher.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch [IO.IOException] {
        Write-Host '系统正在启动，请稍等，网页准备好后会自动打开。'
        return
    }
    try {
        $state = Read-RunState
        if (Test-Ready $state) { Show-Ready $state; return }
        if (@(Get-OwnedProcesses $state).Count -gt 0) {
            throw '系统仍在启动或关闭中，请稍等再双击。'
        }
        $selectedPort = $null
        foreach ($candidate in $Port..($Port + 10)) {
            $probe = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $candidate)
            try { $probe.Start(); $selectedPort = $candidate; break } catch [Net.Sockets.SocketException] {
                # Try the next local port without interrupting the existing program.
            } finally { $probe.Stop() }
        }
        if (-not $selectedPort) { throw '演示端口均被占用，请联系组员处理；没有关闭其他程序。' }
        $dateDirectory = Join-Path $DataPath (Get-Date -Format 'yyyyMMdd')
        $logs = Join-Path $DataPath 'logs'
        $temporary = Join-Path $DataPath 'temp'
        @($dateDirectory, $logs, $temporary) | ForEach-Object {
            if (-not (Test-Path -LiteralPath $_)) { New-Item -ItemType Directory -Path $_ | Out-Null }
        }
        $env:TEMP = $temporary
        $env:TMP = $temporary
        $env:PIP_CACHE_DIR = Join-Path $DataPath 'cache\python'
        $env:npm_config_cache = Join-Path $DataPath 'cache\node'
        $env:PYTHONIOENCODING = 'utf-8'
        $env:PYTHONDONTWRITEBYTECODE = '1'
        $env:PYTHONNOUSERSITE = '1'
        $python = Prepare-Python $state
        $web = Prepare-Web
        $secretPath = Join-Path $dateDirectory 'local-secret.txt'
        if (-not (Test-Path -LiteralPath $secretPath)) {
            $bytes = New-Object byte[] 48
            $random = [Security.Cryptography.RandomNumberGenerator]::Create()
            try { $random.GetBytes($bytes) } finally { $random.Dispose() }
            [IO.File]::WriteAllText($secretPath, [Convert]::ToBase64String($bytes))
        }
        $env:JWT_SECRET = [IO.File]::ReadAllText($secretPath).Trim()
        $env:DATABASE_URL = 'sqlite:///' + (Join-Path $dateDirectory 'hospital.sqlite').Replace('\', '/')
        $env:FRONTEND_DIST = $web
        $env:ALLOWED_ORIGINS = "http://127.0.0.1:$selectedPort"
        $env:AI_PROVIDER = 'disabled'
        $env:PYTHONIOENCODING = 'utf-8'
        $env:PYTHONDONTWRITEBYTECODE = '1'
        $env:PYTHONNOUSERSITE = '1'
        $env:TEMP = $temporary
        $env:TMP = $temporary
        $instance = [Guid]::NewGuid().ToString()
        $arguments = '-u -m scripts.demo_server --state-dir "' + $DataPath + '" --port ' + $selectedPort + ' --instance ' + $instance
        Write-Host '正在启动和序 HIS，首次启动会准备教学演示数据，请稍等……'
        $worker = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $logs ($instance + '.log')) -RedirectStandardError (Join-Path $logs ($instance + '.error.log'))
        $deadline = [DateTime]::UtcNow.AddSeconds(60)
        do {
            Start-Sleep -Milliseconds 400
            $state = Read-RunState
            if ($state -and $state.instance_id -eq $instance) {
                if ($state.status -eq 'failed') { throw ('启动未完成：' + $state.error + '。日志目录：' + $logs) }
                if ($state.status -eq 'stopped') { throw '启动已取消，请重新双击“启动系统.cmd”。' }
                if (Test-Ready $state) { Show-Ready $state; return }
            }
            if ($worker.HasExited) { throw ('启动程序已退出。请把日志目录发给组员：' + $logs) }
        } while ([DateTime]::UtcNow -lt $deadline)
        [IO.File]::WriteAllText((Join-Path $DataPath ('stop-' + $instance + '.signal')), 'stop')
        throw ('启动超时，已请求停止，请把日志目录发给组员：' + $logs)
    } finally { $startLock.Dispose() }
}

try {
    if ($Action -eq 'Start') { Start-Demo } else { Stop-Demo }
    exit 0
} catch {
    Write-Host ''
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
