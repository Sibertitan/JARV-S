# J.A.R.V.I.S Free

GEMİNİ İLE BAĞLANTI İLE ÇALIŞIR. WINDOWS VE LINUX'TA ÇALIŞIR.

Google Gemini ile çalışan, Türkçe kişisel asistan. Linux kurulum adımları aşağıdadır; kurulum betiği Kali Linux içindir.

## Kaynak kod

Uygulama kaynak kodu [`jarvis-free/`](jarvis-free/) klasöründedir. API anahtarını kendin oluştur ve yerel `jarvis-free/config/api_keys.json` dosyasında sakla. Bu dosya Git tarafından yok sayılır; anahtarını issue, pull request veya herkese açık başka bir yere koyma.

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

## Android portu

Bu depoda şu anda Android uygulamasının kaynak kodu veya derlenmiş APK bulunmuyor; yalnızca masaüstü asistanının Python kaynak kodu var. Android geliştiricileri bu açık kaynak kodu temel alarak yerel bir Android istemcisi hazırlayabilir. Masaüstü uygulamasının mevcut telefon arayüzü `8765` portunda `/ping` ve `/ask` uç noktalarını kullanır; istekler JSON içindeki `token` ve `text` alanlarını taşır.

Windows `.exe` ve Android `.apk` dosyaları büyük ikili dosyalar oldukları için depoya eklenmedi.

## Lisans ve katkı

Proje [`Apache License 2.0`](LICENSE) ile yayımlanmıştır. Lisans koşulları kapsamında kaynak kodu inceleyebilir, değiştirebilir ve yeniden dağıtabilirsiniz. Android portu veya iyileştirmeler için pull request açabilirsiniz.
