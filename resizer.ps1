# Chuẩn hoá dung lượng ảnh minh chứng (resizer/)
# Chạy ở thư mục gốc repo: .\resizer.ps1
param(
    [string]$InputDir = "",
    [string]$OutputDir = "",
    [int]$Limit = 0,
    [switch]$Recursive,
    [switch]$DryRun,
    [switch]$SkipExisting,
    [switch]$NoWatermark,
    [switch]$NoEnhance
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Requirements = Join-Path $Root "requirements.txt"
$Script = Join-Path $Root "resizer\resize.py"
$EnvExample = Join-Path $Root "resizer\.env.example"
$EnvFile = Join-Path $Root "resizer\.env"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Tạo .venv..."
    python -m venv (Join-Path $Root ".venv")
    if (-not (Test-Path $VenvPython)) {
        throw "Không tạo được .venv"
    }
}

& $VenvPython -c "import PIL, cv2, onnxruntime" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cài dependency vào .venv..."
    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path $EnvFile) -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "Đã tạo resizer\.env từ .env.example — chỉnh MIN/MAX trước khi chạy."
}

$pyArgs = @($Script)
if ($InputDir) {
    $pyArgs += @("--input", $InputDir)
}
if ($OutputDir) {
    $pyArgs += @("--output", $OutputDir)
}
if ($Limit -gt 0) {
    $pyArgs += @("--limit", "$Limit")
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
if ($NoWatermark) {
    $pyArgs += "--no-watermark"
}
if ($NoEnhance) {
    $pyArgs += "--no-enhance"
}

Write-Host "Resize ảnh minh chứng..."
& $VenvPython @pyArgs
exit $LASTEXITCODE
