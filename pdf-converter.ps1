# Chuyển ảnh trong folder sang PDF (pdf-converter/) — giữ nguyên kích thước, không pad A4
# Chạy ở thư mục gốc repo: .\pdf-converter.ps1
# Hoặc cd vào folder ảnh rồi: D:\path\sv5t\pdf-converter.ps1
param(
    [string]$InputDir = "",
    [string[]]$Ext = @(),
    [switch]$Recursive,
    [switch]$DryRun,
    [switch]$SkipExisting,
    [switch]$DeleteSources,
    [switch]$Quiet,
    [switch]$NoLog,
    [string]$Log = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Requirements = Join-Path $Root "requirements.txt"
$Script = Join-Path $Root "pdf-converter\convert.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Tạo .venv..."
    python -m venv (Join-Path $Root ".venv")
    if (-not (Test-Path $VenvPython)) {
        throw "Không tạo được .venv"
    }
}

& $VenvPython -c "import pymupdf, PIL" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cài dependency vào .venv..."
    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$pyArgs = @($Script)
if ($InputDir) {
    $pyArgs += $InputDir
} else {
    $pyArgs += (Get-Location).Path
}
foreach ($e in $Ext) {
    if ($e) {
        $pyArgs += @("--ext", $e)
    }
}
if ($Recursive) {
    $pyArgs += "--recursive"
}
if ($DryRun) {
    $pyArgs += "--dry-run"
}
if ($SkipExisting) {
    $pyArgs += "--skip-existing"
}
if ($DeleteSources) {
    $pyArgs += "--delete-sources"
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

Write-Host "Chuyển ảnh sang PDF (kích thước gốc)..."
& $VenvPython @pyArgs
exit $LASTEXITCODE
