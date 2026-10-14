# Deploy web-tools lên GitHub Pages (repo riêng) và/hoặc Vercel.
# Chỉ đưa file web lên, không chứa dữ liệu của repo sv5t.
param(
    [string]$Repo = "sv5t-pdf-tools",
    [ValidateSet("all", "github", "vercel")]
    [string]$Target = "all"
)
$ErrorActionPreference = "Continue"
function Check($step) { if ($LASTEXITCODE -ne 0) { throw "Lỗi ở bước: $step" } }

$tmp = Join-Path $env:TEMP "deploy-$Repo"
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
New-Item -ItemType Directory $tmp | Out-Null

Copy-Item "$PSScriptRoot\*.html", "$PSScriptRoot\*.css", "$PSScriptRoot\*.js", "$PSScriptRoot\*.png" $tmp
Copy-Item "$PSScriptRoot\vendor", "$PSScriptRoot\models", "$PSScriptRoot\assets" $tmp -Recurse
New-Item -ItemType File (Join-Path $tmp ".nojekyll") | Out-Null
Set-Content -Path (Join-Path $tmp "CNAME") -Value "sv5t.pntr.dev" -Encoding ascii -NoNewline

Push-Location $tmp
try {
    if ($Target -in "all", "github") {
        $owner = (gh api user --jq .login)
        git -c core.autocrlf=false init -q -b main
        git -c core.autocrlf=false add -A 2>$null
        git commit -q -m "Deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm')"; Check "commit"

        gh repo view "$owner/$Repo" 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            gh repo create $Repo --public --description "Ảnh sang PDF, gộp PDF, nén ảnh, xoá watermark (chạy trên trình duyệt)" --source . --push; Check "tạo repo"
            gh api -X POST "repos/$owner/$Repo/pages" -f "source[branch]=main" -f "source[path]=/" | Out-Null; Check "bật GitHub Pages"
        } else {
            git remote add origin "https://github.com/$owner/$Repo.git"
            git push -q --force origin main; Check "push"
        }
        Write-Host "GitHub Pages (đợi ~1 phút để build): https://$($owner.ToLower()).github.io/$Repo/"
    }

    if ($Target -in "all", "vercel") {
        vercel link --yes --project $Repo 2>&1 | Out-Null; Check "vercel link"
        $out = vercel deploy --prod --yes 2>$null | Out-String; Check "vercel deploy"
        $state = ($out | ConvertFrom-Json).deployment.readyState
        Write-Host "Vercel ($state): https://$Repo.vercel.app/"
    }
} finally {
    Pop-Location
}
