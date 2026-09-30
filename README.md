# J.A.R.V.I.S Free

GEMİNİ İLE ÇALIŞIR. WINDOWS, KALI LINUX VE ANDROID'DE ÇALIŞIR.

Google Gemini ile ücretsiz çalışan, Türkçe kişisel yapay zekâ asistanı. Sohbet eder, bilgisayarı fare-klavye ile kullanır, kod yazıp çalıştırır, sunum hazırlar, WhatsApp'tan mesaj/ses gönderir, hatırlatır ve yetkili Kali laboratuvar testlerini yürütür.

## Kaynak kod

Uygulama kaynak kodu [`jarvis-free/`](jarvis-free/) klasöründedir. API anahtarını kendin oluştur ve yerel `jarvis-free/config/api_keys.json` dosyasında sakla. Bu dosya Git tarafından yok sayılır; anahtarını issue, pull request veya herkese açık başka bir yere koyma.

## Yenilikler (entegrasyonlar)

Bu sürüm, birkaç açık kaynak fikri JARVIS'e yerel olarak ekler — hepsi ücretsiz Gemini beyniyle çalışır. Ayrıntılar: [`jarvis-free/INTEGRATION_STATUS.md`](jarvis-free/INTEGRATION_STATUS.md).

- **Yerleşik kod ajanı (codex):** `code_run` aracı kodu yazar, çalıştırır ve çıktısını (stdout+stderr+çıkış kodu) döndürür; yaz → çalıştır → hatayı gör → düzelt döngüsüyle çalışan program üretir. Python/Node/bash/PowerShell; Windows ve Kali'de yerel, ek API gerektirmez.
- **Telefondan iki işletim sistemini de yönetme:** Android istemcisi komutu `/ask` ile bilgisayara iletir ve orada **tam araçlı ajan** çalışır. JARVIS Windows'ta ise Windows'u, Kali'de ise Kali'yi telefondan tam yönetirsin; mesh ile tek telefondan ikisine birden erişebilirsin.
- **OmniRoute yedeği:** Gemini kotası dolduğunda yerel OmniRoute ağ geçidine otomatik düşer (fallback).
- **Headroom sıkıştırma:** Büyük araç çıktılarını yerelde sıkıştırır; hata olursa güvenle atlar.
- **Kalıcı oturum hafızası (claude-mem tarzı):** `remember_session`/`recall_sessions` ile oturum özetleri kaydedilir ve bir sonraki açılışta bağlama geri yüklenir.
- **Kendini geliştirme günlüğü (task-observer tarzı):** `observe_self`/`review_observations` ile düzeltmeler, tercihler ve eksikler not edilir.
- **Kurulum önerisi (claude-code-setup tarzı):** `recommend_setup` ortamı inceleyip önceliklendirilmiş, uygulanabilir öneriler verir (salt okunur).
- **DaVinci Resolve MCP:** Yerel MCP köprüsüyle (`jarvis_mcp.py`) Resolve araçları JARVIS'ten kullanılabilir.

## Linux'a indirip kurma (Kali Linux)

1. Bu sayfanın üstündeki **Code → Download ZIP** seçeneğiyle projeyi indirip ZIP dosyasını çıkarın.
2. Terminali açıp çıkarılan `JARV-S` klasörünün içindeki `jarvis-free` klasörüne girin.
3. Aşağıdaki komutları sırayla çalıştırın:

```bash
chmod +x install_kali.sh run_kali.sh
./install_kali.sh
./run_kali.sh
```

İlk açılışta ücretsiz Gemini API anahtarı ister; ekrandaki yönergeleri izleyin. Anahtarı daha sonra yerel `config/api_keys.json` dosyasında saklar. JARVIS'i grafik masaüstü oturumunda açın. Ayrıntılar için [`jarvis-free/README.md`](jarvis-free/README.md) dosyasına bakın.

## Android

Android istemcisinin kaynak kodu artık [`jarvis-free/android/`](jarvis-free/android/) klasöründedir. Bu istemci ince bir ağ istemcisidir: aynı Wi-Fi'daki JARVIS bilgisayarına `8765` portundan `/ping` ve `/ask` uç noktalarıyla bağlanır (JSON içinde `token` ve `text`). APK'yı üretmek için klasörü Android Studio ile açın ya da Android SDK 35 kurulu bir makinede `gradlew assembleDebug` çalıştırın. Gemini anahtarı yalnızca bilgisayarda kalır, APK'nın içine gömülmez.

Windows `.exe` ve Android `.apk` dosyaları büyük ikili dosyalar oldukları için depoya eklenmedi.

## Lisans ve katkı

Proje [`Apache License 2.0`](LICENSE) ile yayımlanmıştır. Lisans koşulları kapsamında kaynak kodu inceleyebilir, değiştirebilir ve yeniden dağıtabilirsiniz. Katkı ve iyileştirmeler için pull request açabilirsiniz.
