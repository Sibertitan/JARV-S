# J.A.R.V.I.S — Google Gemini ile ücretsiz sürüm

Bu klasördeki `jarvis_claude.py` uygulamasını Python ile çalıştırır. Windows `.exe` ve Android `.apk` paketleri ayrı dağıtım dosyalarıdır; Kali Linux için kaynak kod kurulumunu kullanın.

## Kali Linux kurulumu

1. Bu proje klasörünü Kali bilgisayarına aktarın.
2. Terminalde klasöre girip `chmod +x install_kali.sh run_kali.sh` komutunu çalıştırın.
3. `./install_kali.sh` komutunu çalıştırın. Python sanal ortamını ve ses/arayüz bağımlılıklarını kurar.
4. Gemini API anahtarı `config/api_keys.json` dosyasında hazırdır. Uygulama ilk açılışta anahtar sormaz. Anahtarı değiştirmek için bu dosyayı düzenleyin; dosyayı paylaşmayın veya depoya eklemeyin.
5. `./run_kali.sh` ile JARVIS'i açın.

Mikrofon izni ve masaüstü oturumu gerektiğinden JARVIS'i grafik oturumu içindeki terminalden başlatın. Sesli yanıt için `ffplay` kurulum betiğine dahildir.

## Telefonda veya Windows'tan erişim

Uygulama açıkken aynı Wi-Fi ağına bağlı telefondan ya da Windows bilgisayardan, ekranda gösterilen IP adresi ve güvenlik koduyla bağlanın. Gelen istekler JARVIS'in mevcut Gemini/yerel sağlayıcısından yürütülür. Başka bir ağdan erişim için ayrıca `cloudflared` kurup PATH'e ekleyin; JARVIS kuruluysa mevcut tünel desteğini kullanır. Güvenlik kodu ayar dosyasında tutulur; dışarıya açık tünel URL'sini ve kodu başkalarıyla paylaşmayın.

## Özellik ve platform notu

Sohbet, mikrofon, hatırlatıcılar ve telefon üzerinden soru sorma Kali'de çalışacak şekilde hazırlanmıştır. Fare/klavye kontrolü ve bazı uygulama entegrasyonları Windows'a özgü API ve uygulamalara dayanır; Kali'de bu Windows özelliklerinin tümü mevcut olmayabilir. Görsel/video araçları işletim sisteminde bulunan dosya konumları ve yazı tiplerini kullanır.

## Windows ve Android

Windows'ta `JARVIS Ucretsiz.exe` çalıştırılabilir. Android'de `JARVIS_Ucretsiz_Telefon.apk` telefona kurulur. Kali'den erişim için Android istemcisi, uygulama açık olan Kali bilgisayarının IP/port bilgilerine bağlanmalıdır.

## Anahtar güvenliği

`config/api_keys.json` Git tarafından izlenmez. Anahtarın yanlışlıkla herkese açık bir yerde paylaşıldığını düşünüyorsanız Google AI Studio'dan iptal edip yenisini oluşturun.
