param(
    [string]$PythonPath = 'D:\rubbish\zhongjian\envs\医院信息系统\dev\Scripts\python.exe',
    [string]$NodePath = 'D:\Code\nodejs\node.exe',
    [string]$DatabasePath = 'D:\rubbish\zhongjian\artifacts\医院信息系统\demo\hospital.sqlite',
    [string]$WebPath = 'D:\rubbish\zhongjian\build\医院信息系统\frontend',
    [int]$Port = 8000,
    [switch]$Build,
    [switch]$Showcase
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonPath)) { throw '未找到项目 Python。先按 README 准备环境，或通过 -PythonPath 指定。' }
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { throw "端口 $Port 已被占用；不停止已有进程。请通过 -Port 指定空闲端口。" }
$taskTemp = 'D:\rubbish\zhongjian\temp\医院信息系统\local-demo'
@($taskTemp, (Split-Path -Parent $DatabasePath)) | ForEach-Object { if (-not (Test-Path -LiteralPath $_)) { New-Item -ItemType Directory -Path $_ | Out-Null } }
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$env:PYTHONDONTWRITEBYTECODE = '1'
if ($Build) {
    $npmCli = Join-Path (Split-Path -Parent $NodePath) 'node_modules\npm\bin\npm-cli.js'
    $env:VITE_API_BASE_URL = '/api'
    $env:npm_config_cache = 'D:\rubbish\zhongjian\caches\node'
    & $NodePath $npmCli run build --prefix (Join-Path $PSScriptRoot 'frontend') -- --outDir $WebPath
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
}
if (-not (Test-Path -LiteralPath (Join-Path $WebPath 'index.html'))) { throw '没有找到前端构建文件。首次启动添加 -Build，或者通过 -WebPath 指定交付包中的 web 目录。' }
$env:DATABASE_URL = 'sqlite:///' + $DatabasePath.Replace('\','/')
$env:FRONTEND_DIST = $WebPath
$env:ALLOWED_ORIGINS = "http://127.0.0.1:$Port"
$secretPath = Join-Path (Split-Path -Parent $DatabasePath) 'local-secret.txt'
if (-not (Test-Path -LiteralPath $secretPath)) {
    $bytes = New-Object byte[] 48
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $random.GetBytes($bytes) } finally { $random.Dispose() }
    [IO.File]::WriteAllText($secretPath, [Convert]::ToBase64String($bytes))
}
$env:JWT_SECRET = [IO.File]::ReadAllText($secretPath).Trim()
$env:AI_PROVIDER = 'disabled'
Push-Location (Join-Path $PSScriptRoot 'backend')
try {
    & $PythonPath -m scripts.init_db
    if ($LASTEXITCODE -ne 0) { throw '迁移失败，保留数据与备份。' }
    & $PythonPath -m scripts.seed
    if ($LASTEXITCODE -ne 0) { throw '演示初始化失败' }
    if ($Showcase) {
        & $PythonPath -m scripts.seed_showcase
        if ($LASTEXITCODE -ne 0) { throw '课堂展示场景初始化失败；请使用新的独立演示数据库。' }
    }
    Write-Host "本机演示：http://127.0.0.1:$Port ；在本终端按 Ctrl+C 停止。"
    & $PythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
