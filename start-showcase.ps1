param(
    [string]$PythonPath = 'D:\rubbish\zhongjian\envs\医院信息系统\dev\Scripts\python.exe',
    [int]$Port = 8000,
    [switch]$Build
)
$showcaseDate = Get-Date -Format 'yyyyMMdd'
$showcaseDatabase = Join-Path 'D:\rubbish\zhongjian\artifacts\医院信息系统\高分升级-20261029\demo' "$showcaseDate\hospital.sqlite"
$showcaseWeb = 'D:\rubbish\zhongjian\build\医院信息系统\high-score\frontend'
$buildNeeded = $Build -or -not (Test-Path -LiteralPath (Join-Path $showcaseWeb 'index.html'))
& (Join-Path $PSScriptRoot 'start-demo.ps1') -PythonPath $PythonPath -DatabasePath $showcaseDatabase -WebPath $showcaseWeb -Port $Port -Build:$buildNeeded -Showcase
