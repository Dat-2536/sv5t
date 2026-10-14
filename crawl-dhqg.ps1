# Cào hồ sơ và tiêu chí SV5T ĐHQG từ data.xlsx ra Excel.
# Chạy ở thư mục gốc repo: .\crawl-dhqg.ps1
param(
    [string]$Data = "",
    [int]$Limit = 0,
    [int]$Workers = 6,
    [int]$Retries = 2,
    [string]$Account = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Requirements = Join-Path $Root "requirements.txt"
$Crawl = Join-Path $Root "crawl-dhqg\crawl.py"

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

$DataFile = if ($Data) { $Data } else { Join-Path $Root "crawl-dhqg\data.xlsx" }
$crawlArgs = @($Crawl, $DataFile)
if ($Account) {
    $crawlArgs += @("--account", $Account)
}
if ($Limit -gt 0) {
    $crawlArgs += @("--limit", "$Limit")
}
if ($Workers -gt 0) {
    $crawlArgs += @("--workers", "$Workers")
}
$crawlArgs += @("--retries", "$Retries")

Write-Host "Cào hồ sơ SV5T ĐHQG..."
& $VenvPython @crawlArgs
exit $LASTEXITCODE
