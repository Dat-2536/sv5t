# Tạo tài khoản SV5T ĐHQG từ data.xlsx, rồi kiểm tra lại hồ sơ trên web.
# Chạy ở thư mục gốc repo: .\register-dhqg.ps1
param(
    [int]$Limit = 0,
    [int]$Pause = 15,
    [string]$ChromeProfiles = "",
    [int]$BatchSize = 7,
    [int]$CaptchaRetries = 5,
    [switch]$RefreshChromeProfile,
    [switch]$ValidateOnly,
    [switch]$SkipValidate,
    [switch]$FreshChrome
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Requirements = Join-Path $Root "requirements.txt"
$Register = Join-Path $Root "register-dhqg\register.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Tạo .venv..."
    python -m venv (Join-Path $Root ".venv")
    if (-not (Test-Path $VenvPython)) {
        throw "Không tạo được .venv"
    }
}

& $VenvPython -c "import openpyxl, patchright, websocket" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cài dependency vào .venv..."
    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$common = @($Register)
if ($Limit -gt 0) {
    $common += @("--limit", "$Limit")
}

if (-not $ValidateOnly) {
    if (-not $FreshChrome) {
        $chrome = Get-Process chrome -ErrorAction SilentlyContinue
        if ($chrome) {
            Write-Host "Chrome đang mở. Đóng hết cửa sổ Chrome rồi chạy lại."
            exit 1
        }
    }
    $registerArgs = @($common)
    if (-not $FreshChrome) {
        $registerArgs += "--use-chrome-profile"
        if ($Pause -gt 0) {
            $registerArgs += @("--pause", "$Pause")
        }
        if ($ChromeProfiles) {
            $registerArgs += @("--chrome-profiles", $ChromeProfiles)
        }
        $registerArgs += @("--batch-size", "$BatchSize", "--captcha-retries", "$CaptchaRetries")
        if ($RefreshChromeProfile) {
            $registerArgs += "--refresh-chrome-profile"
        }
    }
    Write-Host "Đăng ký tài khoản..."
    & $VenvPython @registerArgs
    $registerCode = $LASTEXITCODE
    if ($registerCode -ne 0) {
        Write-Host "Đăng ký kết thúc với mã $registerCode. Vẫn kiểm tra những dòng đã có trên web."
    }
}

if (-not $SkipValidate) {
    Write-Host "Kiểm tra hồ sơ..."
    & $VenvPython @common --validate
    $validateCode = $LASTEXITCODE
}

if ($registerCode -and $registerCode -ne 0) {
    exit $registerCode
}
if ($null -ne $validateCode -and $validateCode -ne 0) {
    exit $validateCode
}
exit 0
