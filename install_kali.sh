#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
sudo apt update

# Çekirdek bağımlılıklar (bunlar olmazsa uygulama çalışmaz)
sudo apt install -y python3 python3-venv python3-tk python3-xlib python3-dev build-essential \
  portaudio19-dev ffmpeg libportaudio2 xclip fonts-dejavu-core git gh

# Ek özellikler (ses, medya tuşları, ekran kontrolü, Tor). Biri bulunamazsa kurulum durmasın:
for pkg in espeak-ng playerctl pulseaudio-utils xdg-utils scrot xdotool wmctrl tor torbrowser-launcher; do
  sudo apt install -y "$pkg" || echo "UYARI: $pkg kurulamadi, atlaniyor."
done

# Tor anonim modu: kontrol portunu (yeni IP için) çerez kimlik doğrulamasıyla aç
TORRC=/etc/tor/torrc
if [[ -f "$TORRC" ]]; then
  grep -q "^ControlPort 9051" "$TORRC" || echo "ControlPort 9051" | sudo tee -a "$TORRC" >/dev/null
  grep -q "^CookieAuthentication 1" "$TORRC" || echo "CookieAuthentication 1" | sudo tee -a "$TORRC" >/dev/null
  grep -q "^CookieAuthFileGroupReadable 1" "$TORRC" || echo "CookieAuthFileGroupReadable 1" | sudo tee -a "$TORRC" >/dev/null
  sudo usermod -aG debian-tor "$USER" 2>/dev/null || true   # çerez dosyasını okuyabilmek için
  sudo systemctl enable tor 2>/dev/null || true
  sudo systemctl restart tor 2>/dev/null || sudo service tor restart 2>/dev/null || true
fi
# Kali güvenlik framework/araçları — JARVIS'in kullanabilmesi için (best-effort; biri yoksa atlanır).
# Kali'de çoğu zaten kuruludur; eksik olanlar tamamlanır. İnternet ve süre gerektirir.
if grep -qi kali /etc/os-release 2>/dev/null; then
  echo "Kali güvenlik araçları kontrol ediliyor/kuruluyor (eksikler tamamlanır)..."
  for pkg in nmap masscan rustscan netdiscover arp-scan dnsrecon dnsenum theharvester recon-ng \
             spiderfoot amass sublist3r whatweb wafw00f nikto nuclei wpscan sqlmap commix wfuzz \
             ffuf feroxbuster gobuster dirb dirsearch metasploit-framework exploitdb set beef-xss \
             impacket-scripts crackmapexec netexec bloodhound bloodhound.py responder mitm6 kerbrute \
             evil-winrm certipy-ad smbmap enum4linux-ng ldap-utils hydra medusa ncrack john hashcat \
             hashid cewl crunch seclists wordlists aircrack-ng wifite kismet reaver bully bettercap \
             hcxtools hcxdumptool wireshark tshark tcpdump ettercap-graphical dsniff macchanger \
             mitmproxy sslscan testssl.sh radare2 gdb ltrace strace binwalk exiftool foremost steghide stegseek \
             volatility3 apktool jadx dex2jar frida adb chisel proxychains4 socat sshuttle \
             docker.io trivy python3-scapy python3-pywifi python3-impacket \
             yara python3-yara pev ssdeep python3-oletools clamav cabextract sigma-cli capstone; do
    dpkg -s "$pkg" >/dev/null 2>&1 || sudo apt install -y "$pkg" 2>/dev/null || echo "  atlandi: $pkg"
  done
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
# JARVIS'in yazacağı güvenlik scriptleri için sık kullanılan Python kütüphaneleri (best-effort)
.venv/bin/python -m pip install scapy pywifi python-nmap paramiko requests pycryptodome impacket 2>/dev/null || true
# Malware analiz + tespit araçları (savunma tarafı): YARA kuralları, capa, floss
.venv/bin/python -m pip install yara-python capa flare-floss 2>/dev/null || true
[[ -f config/api_keys.json ]] || cp config/api_keys.example.json config/api_keys.json
chmod 600 config/api_keys.json 2>/dev/null || true
echo "Kurulum tamamlandi. Baslatmak icin ./run_kali.sh calistirin."
