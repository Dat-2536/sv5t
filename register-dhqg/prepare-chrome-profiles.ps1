# Sao profile Chrome hàng ngày thành nhiều thư mục để luân phiên khi đăng ký.
# Sau khi chạy script này, mở từng profile một lần bằng Chrome, đăng nhập Google khác nhau,
# vào https://youth.vnuhcm.edu.vn/ rồi đóng Chrome trước khi chạy register-dhqg.ps1.
param(
    [int]$Count = 3
)

$ErrorActionPreference = "Stop"
$Source = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data"
$Root = Join-Path $env:LOCALAPPDATA "sv5t-chrome-profiles"
if (-not (Test-Path $Source)) {
    throw "Không thấy profile Chrome tại $Source"
}
New-Item -ItemType Directory -Path $Root -Force | Out-Null
$names = @("Cookies", "Network", "Preferences", "Secure Preferences", "History", "Bookmarks", "Local Storage", "Session Storage", "Favicons", "Web Data", "Login Data")
for ($i = 1; $i -le $Count; $i++) {
    $target = Join-Path $Root "google-$i"
    if (Test-Path $target) {
        Remove-Item $target -Recurse -Force
    }
    $default = Join-Path $target "Default"
    New-Item -ItemType Directory -Path $default -Force | Out-Null
    Copy-Item (Join-Path $Source "Local State") $target -Force
    foreach ($name in $names) {
        $item = Join-Path $Source "Default\$name"
        if (Test-Path $item) {
            Copy-Item $item (Join-Path $default $name) -Recurse -Force
        }
    }
    Write-Host "Đã tạo $target"
}
Write-Host "Tiếp theo: mở Chrome với từng thư mục, đăng nhập Google khác nhau, vào youth.vnuhcm.edu.vn một lần."
Write-Host "Chạy đăng ký: .\register-dhqg.ps1 -ChromeProfiles `"$Root`""
