# J.A.R.V.I.S — Ücretsiz Sürüm (Google Gemini)

Windows ve Android için, **ücretsiz Google Gemini** ile çalışan kişisel yapay zekâ asistanı.
Konuşarak ya da yazarak kullan: uygulama açma, WhatsApp mesaj/sesli mesaj/arama, müzik (Spotify),
fotoğraf/görsel düzenleme, video düzenleme, sunum, hatırlatıcı, hava durumu, sohbet ve daha fazlası.

Herkes **kendi ücretsiz Gemini API anahtarını** girer — kimse başkasının anahtarını kullanmaz.

## Ücretsiz Gemini anahtarı alma (1 dakika)
1. https://aistudio.google.com/apikey adresine git
2. Google ile giriş yap → **Create API key**
3. Anahtarı kopyala

## Windows
1. `JARVIS Ucretsiz.exe` dosyasına çift tıkla.
   - "Windows korudu" uyarısı çıkarsa: **Daha fazla bilgi → Yine de çalıştır**
2. Açılan kutuya Gemini anahtarını yapıştır (sadece ilk kurulumda sorulur).
3. Hazır. `offline` ve `config` klasörleri exe ile aynı yerde kalmalı.

> Kaynaktan çalıştırmak istersen: `python jarvis_claude.py` (Python 3.11+ ve
> `pip install -r requirements.txt`).

## Android
1. `JARVIS_Ucretsiz_Telefon.apk` dosyasını telefona at, kur
   ("bilinmeyen uygulama" uyarısına izin ver).
2. Aç → Gemini anahtarını yapıştır (bir kez).

## Gizlilik
- Anahtarın yalnızca **kendi cihazındaki** ayar/config dosyasında tutulur.
- Bu depoda hiçbir API anahtarı yoktur (`config/api_keys.json` boştur).

## Not
Sesli konuşma ve bazı özellikler internet ister. Beyin: Google Gemini (ücretsiz kotayla).

---
Geliştiren: **Ali İhsan Kahraman**
