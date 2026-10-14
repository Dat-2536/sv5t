# Highlight PDF danh sách theo MSSV trong highlighter/data.xlsx
# Chạy ở thư mục gốc repo: .\highlighter.ps1
param(
    [string]$Root = "",
    [string]$Data = "",
    [string]$OutputDir = "",
    [string]$Faculty = "",
    [string[]]$Only = @(),
    [int]$Limit = 0,
    [switch]$DryRun,
    [switch]$SkipExisting,
    [switch]$NoCache,
    [switch]$RefreshCache,
    [switch]$CleanOutput,
    [switch]$Quiet,
    [switch]$NoLog,
    [string]$Log = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Script = Join-Path $RepoRoot "highlighter\highlight.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Tạo .venv..."
    python -m venv (Join-Path $RepoRoot ".venv")
    if (-not (Test-Path $VenvPython)) {
        throw "Không tạo được .venv"
    }
}

Write-Host "Cài dependency highlighter (pymupdf, rapidocr...)..."
& $VenvPython -m pip install -q pymupdf openpyxl rapidocr-onnxruntime opencv-python-headless numpy

$pyArgs = @($Script)
if ($Root) { $pyArgs += @("--root", $Root) }
if ($Data) { $pyArgs += @("--data", $Data) }
if ($OutputDir) { $pyArgs += @("--output", $OutputDir) }
if ($Faculty) { $pyArgs += @("--faculty", $Faculty) }
foreach ($folder in $Only) {
    if ($folder) { $pyArgs += @("--only", $folder) }
}
if ($Limit -gt 0) { $pyArgs += @("--limit", $Limit) }
if ($DryRun) { $pyArgs += "--dry-run" }
if ($SkipExisting) { $pyArgs += "--skip-existing" }
if ($NoCache) { $pyArgs += "--no-cache" }
if ($RefreshCache) { $pyArgs += "--refresh-cache" }
if ($CleanOutput) { $pyArgs += "--clean-output" }
if ($Quiet) { $pyArgs += "--quiet" }
if ($NoLog) { $pyArgs += "--no-log" }
if ($Log) { $pyArgs += @("--log", $Log) }

& $VenvPython @pyArgs
exit $LASTEXITCODE
