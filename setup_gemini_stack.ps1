# =============================================================================
#  JARVIS - Gemini Stack Kurulumu (Windows / PowerShell)
# -----------------------------------------------------------------------------
#  Amac: Claude ekosistemi araclarini (Claude Code Setup, Claude Mem,
#  Task Observer) ve Headroom'u, ZATEN kurulu olan OmniRoute agiz gecidi
#  uzerinden GEMINI altyapisinda calistirmak.
#
#  Mimari:
#    Arac  ->  OmniRoute (http://127.0.0.1:20128)  ->  Gemini
#    OmniRoute hem OpenAI-uyumlu hem Anthropic-uyumlu /v1 sunar; bu yuzden
#    Claude Code'un uc noktasini OmniRoute'a cevirmek, onun icindeki
#    tum eklenti/skill'leri (Claude Mem, Task Observer, Claude Code Setup)
#    tek seferde Gemini'ye yonlendirir.
#
#  Kullanim:   powershell -ExecutionPolicy Bypass -File .\setup_gemini_stack.ps1
#  Anahtar:    -OmniKey "<OmniRoute Dashboard -> Endpoints anahtari>"
#              (bos birakilirsa serbest/zero-config anahtari 'omniroute' denenir)
# =============================================================================
param(
    [string]$OmniKey = "omniroute",
    [string]$OmniHost = "http://127.0.0.1:20128"
)

$ErrorActionPreference = "Stop"
$Root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$OmniDir = Join-Path $Root "work\omniroute-local"
$OmniBin = Join-Path $OmniDir "node_modules\.bin\omniroute.CMD"
$ApiV1  = "$OmniHost/v1"

function Info($m){ Write-Host "[JARVIS] $m" -ForegroundColor Cyan }
function Ok($m){ Write-Host "[OK]    $m" -ForegroundColor Green }
function Warn($m){ Write-Host "[UYARI] $m" -ForegroundColor Yellow }

# --- 1) OmniRoute calisiyor mu? Degilse baslat -------------------------------
function Test-Omni {
    try { (Invoke-WebRequest -Uri "$OmniHost/api/init" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 }
    catch { $false }
}

Info "OmniRoute durumu kontrol ediliyor ($OmniHost)..."
if (Test-Omni) {
    Ok "OmniRoute zaten calisiyor."
} else {
    if (-not (Test-Path $OmniBin)) { throw "OmniRoute bulunamadi: $OmniBin (once 'pnpm install' work\omniroute-local icinde)" }
    Info "OmniRoute baslatiliyor..."
    $env:HOSTNAME = "127.0.0.1"; $env:OMNIROUTE_BOUND_HOST = "127.0.0.1"; $env:PORT = "20128"
    Start-Process -FilePath $OmniBin -ArgumentList @("serve","--port","20128","--no-open","--no-tray") -WorkingDirectory $OmniDir -WindowStyle Hidden
    for ($i=0; $i -lt 30 -and -not (Test-Omni); $i++) { Start-Sleep -Seconds 1 }
    if (Test-Omni) { Ok "OmniRoute basladi." } else { Warn "OmniRoute acilmadi; dashboard'u elle kontrol et." }
}

# --- 2) Claude Code + eklentileri (Claude Mem, Task Observer, Setup) ----------
#     Claude Code'un uc noktasini OmniRoute'a cevir -> icindeki tum
#     eklenti/skill'ler Gemini uzerinden calisir.
Info "Claude Code -> OmniRoute (Gemini) ortam degiskenleri ayarlaniyor..."
[Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $OmniHost, "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", $OmniKey, "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $OmniKey, "User")
$env:ANTHROPIC_BASE_URL = $OmniHost; $env:ANTHROPIC_AUTH_TOKEN = $OmniKey; $env:ANTHROPIC_API_KEY = $OmniKey
Ok "Claude Code artik OmniRoute'a baglaniyor (kalici kullanici ortam degiskeni)."

# --- 3) Headroom + OpenAI-uyumlu araclar -------------------------------------
Info "Headroom / OpenAI-uyumlu araclar -> OmniRoute ayarlaniyor..."
[Environment]::SetEnvironmentVariable("OPENAI_BASE_URL", $ApiV1, "User")
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $OmniKey, "User")
[Environment]::SetEnvironmentVariable("HEADROOM_BASE_URL", $ApiV1, "User")
[Environment]::SetEnvironmentVariable("HEADROOM_API_KEY", $OmniKey, "User")
$env:OPENAI_BASE_URL = $ApiV1; $env:OPENAI_API_KEY = $OmniKey
Ok "Headroom / OpenAI-uyumlu araclar OmniRoute'a baglandi."

# --- 4) Ozet ------------------------------------------------------------------
Write-Host ""
Info "===================== SONRAKI ADIMLAR (elle) ====================="
Write-Host " 1) OmniRoute dashboard'u ac:  $OmniHost/dashboard" -ForegroundColor White
Write-Host "    Providers -> Gemini -> config\api_keys.json icindeki Gemini" -ForegroundColor White
Write-Host "    anahtarini ekle. (OmniRoute kendi yerel DB'sinde saklar.)" -ForegroundColor White
Write-Host "    Endpoints sekmesinden gercek OmniRoute anahtarini kopyalayip" -ForegroundColor White
Write-Host "    bu betigi -OmniKey '<anahtar>' ile bir kez daha calistir." -ForegroundColor White
Write-Host " 2) Yeni bir terminal ac (ortam degiskenleri orada aktif olur)." -ForegroundColor White
Write-Host " 3) Kurulmadiysalar araclari kur, hepsi otomatik OmniRoute->Gemini kullanir:" -ForegroundColor White
Write-Host "      Claude Code Setup : claude icinde  /plugin  ile 'claude-code-setup'" -ForegroundColor Gray
Write-Host "      Claude Mem        : npm i -g claude-mem ; claude-mem install" -ForegroundColor Gray
Write-Host "      Task Observer     : claude icinde /plugin -> one-skill-to-rule-them-all" -ForegroundColor Gray
Write-Host "      Headroom          : kendi kurulumu; ustteki HEADROOM_BASE_URL'i kullanir" -ForegroundColor Gray
Write-Host " 4) JARVIS: switch_brain omniroute  ile beynini Gemini'ye (OmniRoute) al." -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
Ok "Kurulum tamam. Test: yeni terminalde  claude --version  ve  echo %ANTHROPIC_BASE_URL%"
