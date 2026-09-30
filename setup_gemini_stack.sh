#!/usr/bin/env bash
# =============================================================================
#  JARVIS - Gemini Stack Kurulumu (Kali / Linux)
# -----------------------------------------------------------------------------
#  Amac: Claude ekosistemi araclarini (Claude Code Setup, Claude Mem,
#  Task Observer) ve Headroom'u, ZATEN kurulu OmniRoute agiz gecidi
#  uzerinden GEMINI altyapisinda calistirmak.
#
#  Mimari:  Arac -> OmniRoute (http://127.0.0.1:20128) -> Gemini
#  OmniRoute hem OpenAI-uyumlu hem Anthropic-uyumlu /v1 sunar; Claude Code'un
#  uc noktasini OmniRoute'a cevirmek, icindeki tum eklenti/skill'leri
#  (Claude Mem, Task Observer, Claude Code Setup) tek seferde Gemini'ye alir.
#
#  Kullanim:  ./setup_gemini_stack.sh [OMNIROUTE_ANAHTARI]
#             (bos: serbest/zero-config anahtari 'omniroute' denenir)
# =============================================================================
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

OMNI_KEY="${1:-omniroute}"
OMNI_HOST="http://127.0.0.1:20128"
API_V1="$OMNI_HOST/v1"
OMNI_DIR="$PWD/work/omniroute-local"
OMNI_BIN="$OMNI_DIR/node_modules/.bin/omniroute"

info(){ echo -e "\e[36m[JARVIS]\e[0m $*"; }
ok(){   echo -e "\e[32m[OK]\e[0m    $*"; }
warn(){ echo -e "\e[33m[UYARI]\e[0m $*"; }

omni_up(){ curl -fsS --max-time 3 "$OMNI_HOST/api/init" >/dev/null 2>&1; }

# --- 1) OmniRoute calisiyor mu? Degilse baslat -------------------------------
info "OmniRoute durumu kontrol ediliyor ($OMNI_HOST)..."
if omni_up; then
  ok "OmniRoute zaten calisiyor."
else
  [[ -x "$OMNI_BIN" ]] || { echo "OmniRoute bulunamadi: $OMNI_BIN (once work/omniroute-local icinde 'pnpm install')"; exit 1; }
  info "OmniRoute baslatiliyor..."
  ( cd "$OMNI_DIR" && HOSTNAME=127.0.0.1 OMNIROUTE_BOUND_HOST=127.0.0.1 PORT=20128 \
      nohup "$OMNI_BIN" serve --port 20128 --no-open --no-tray >/tmp/omniroute.log 2>&1 & )
  for _ in $(seq 1 30); do omni_up && break; sleep 1; done
  omni_up && ok "OmniRoute basladi." || warn "OmniRoute acilmadi; /tmp/omniroute.log kontrol et."
fi

# --- 2) Claude Code + eklentileri (Claude Mem, Task Observer, Setup) ----------
#     Claude Code'un uc noktasini OmniRoute'a cevir -> tum eklenti/skill Gemini'de.
ENVFILE="$HOME/.jarvis_gemini_stack.env"
cat > "$ENVFILE" <<EOF
# JARVIS Gemini stack - kaynak: source ~/.jarvis_gemini_stack.env
export ANTHROPIC_BASE_URL="$OMNI_HOST"
export ANTHROPIC_AUTH_TOKEN="$OMNI_KEY"
export ANTHROPIC_API_KEY="$OMNI_KEY"
export OPENAI_BASE_URL="$API_V1"
export OPENAI_API_KEY="$OMNI_KEY"
export HEADROOM_BASE_URL="$API_V1"
export HEADROOM_API_KEY="$OMNI_KEY"
EOF
# Oturum acilislarinda otomatik yuklensin (bir kez ekle)
LINE="[ -f \"$ENVFILE\" ] && source \"$ENVFILE\""
grep -qxF "$LINE" "$HOME/.bashrc" 2>/dev/null || echo "$LINE" >> "$HOME/.bashrc"
# shellcheck disable=SC1090
source "$ENVFILE"
ok "Claude Code + Headroom + OpenAI-uyumlu araclar OmniRoute'a baglandi ($ENVFILE)."

# --- 3) Ozet ------------------------------------------------------------------
echo
info "===================== SONRAKI ADIMLAR (elle) ====================="
echo " 1) OmniRoute dashboard:  $OMNI_HOST/dashboard"
echo "    Providers -> Gemini -> config/api_keys.json'daki Gemini anahtarini ekle."
echo "    Endpoints sekmesinden gercek anahtari kopyala, betigi tekrar calistir:"
echo "        ./setup_gemini_stack.sh <ANAHTAR>"
echo " 2) Yeni terminal ac (veya: source ~/.jarvis_gemini_stack.env)."
echo " 3) Araclari kur (hepsi otomatik OmniRoute->Gemini kullanir):"
echo "      Claude Code Setup : claude icinde /plugin -> claude-code-setup"
echo "      Claude Mem        : npm i -g claude-mem && claude-mem install"
echo "      Task Observer     : claude icinde /plugin -> one-skill-to-rule-them-all"
echo "      Headroom          : kendi kurulumu; HEADROOM_BASE_URL'i kullanir"
echo " 4) JARVIS: switch_brain omniroute  ile beyni Gemini'ye (OmniRoute) al."
echo "=================================================================="
ok "Kurulum tamam. Test:  echo \$ANTHROPIC_BASE_URL"
