#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
sudo apt update
sudo apt install -y python3 python3-venv python3-tk python3-xlib python3-dev build-essential portaudio19-dev ffmpeg libportaudio2 xclip fonts-dejavu-core
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
chmod 600 config/api_keys.json 2>/dev/null || true
echo "Kurulum tamamlandi. Baslatmak icin ./run_kali.sh calistirin."
