# Tải ảnh thẻ sinh viên từ myBk HCMUT theo data.xlsx
# Chạy ở thư mục gốc repo: .\crawl-profile-image-mybk.ps1
param(
    [int]$Limit = 0,
    [switch]$SkipExisting
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Requirements = Join-Path $Root "requirements.txt"
$Crawl = Join-Path $Root "crawl-profile-image-mybk\crawl.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Tạo .venv..."
    python -m venv (Join-Path $Root ".venv")
    if (-not (Test-Path $VenvPython)) {
        throw "Không tạo được .venv"
    }
}

& $VenvPython -c "import openpyxl" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cài dependency vào .venv..."
    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$crawlArgs = @($Crawl)
if ($Limit -gt 0) {
    $crawlArgs += @("--limit", "$Limit")
}
if ($SkipExisting) {
    $crawlArgs += "--skip-existing"
}

Write-Host "Tải ảnh thẻ myBk..."
& $VenvPython @crawlArgs
exit $LASTEXITCODE
