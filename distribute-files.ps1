# Phân phối file renamer/output -> distribute-files/output/<mssv>_<họ tên>/
# Chạy ở thư mục gốc repo: .\distribute-files.ps1
param(
    [string]$InputDir = "",
    [string]$OutputDir = "",
    [string[]]$Only = @(),
    [int]$Limit = 0,
    [switch]$Move,
    [switch]$DryRun,
    [switch]$SkipExisting,
    [switch]$NoRecursive,
    [switch]$CleanOutput,
    [switch]$Quiet,
    [switch]$NoLog,
    [string]$Log = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Script = Join-Path $Root "distribute-files\distribute.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Tạo .venv..."
    python -m venv (Join-Path $Root ".venv")
    if (-not (Test-Path $VenvPython)) {
        throw "Không tạo được .venv"
    }
}

$pyArgs = @($Script)
if ($InputDir) {
    $pyArgs += @("--input", $InputDir)
}
if ($OutputDir) {
    $pyArgs += @("--output", $OutputDir)
}
foreach ($folder in $Only) {
    if ($folder) {
        $pyArgs += @("--only", $folder)
    }
}
if ($Limit -gt 0) {
    $pyArgs += @("--limit", "$Limit")
}
if ($Move) {
    $pyArgs += "--move"
}
if ($DryRun) {
    $pyArgs += "--dry-run"
}
if ($SkipExisting) {
    $pyArgs += "--skip-existing"
}
if ($NoRecursive) {
    $pyArgs += "--no-recursive"
}
if ($CleanOutput) {
    $pyArgs += "--clean-output"
}
if ($Quiet) {
    $pyArgs += "--quiet"
}
if ($NoLog) {
    $pyArgs += "--no-log"
}
if ($Log) {
    $pyArgs += @("--log", $Log)
}

Write-Host "Phân phối file theo sinh viên..."
& $VenvPython @pyArgs
exit $LASTEXITCODE
