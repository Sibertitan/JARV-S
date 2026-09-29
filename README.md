# J.A.R.V.I.S Free

Google Gemini ile çalışan, Türkçe kişisel asistan. Kaynak kodu Windows ve Kali Linux masaüstünde çalışacak şekilde düzenlenmiştir.

## Kaynak kod

Uygulama kaynak kodu [`jarvis-free/`](jarvis-free/) klasöründedir. API anahtarını kendin oluştur ve yerel `jarvis-free/config/api_keys.json` dosyasında sakla. Bu dosya Git tarafından yok sayılır; anahtarını issue, pull request veya herkese açık başka bir yere koyma.

## Kali Linux

```bash
cd jarvis-free
chmod +x install_kali.sh run_kali.sh
./install_kali.sh
./run_kali.sh
```

Kali’de grafik masaüstü oturumu gerekir. Ayrıntılar için [`jarvis-free/README.md`](jarvis-free/README.md) dosyasına bak.

## Android portu

Bu depoda şu anda Android uygulamasının kaynak kodu veya derlenmiş APK bulunmuyor; yalnızca masaüstü asistanının Python kaynak kodu var. Android geliştiricileri bu açık kaynak kodu temel alarak yerel bir Android istemcisi hazırlayabilir. Masaüstü uygulamasının mevcut telefon arayüzü `8765` portunda `/ping` ve `/ask` uç noktalarını kullanır; istekler JSON içindeki `token` ve `text` alanlarını taşır.

Windows `.exe` ve Android `.apk` dosyaları büyük ikili dosyalar oldukları için depoya eklenmedi.

## Lisans ve katkı

Proje [`Apache License 2.0`](LICENSE) ile yayımlanmıştır. Lisans koşulları kapsamında kaynak kodu inceleyebilir, değiştirebilir ve yeniden dağıtabilirsiniz. Android portu veya iyileştirmeler için pull request açabilirsiniz.
