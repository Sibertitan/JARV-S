# J.A.R.V.I.S — Google Gemini ile ücretsiz sürüm

Bu klasördeki `jarvis_claude.py` uygulamasını Python ile çalıştırır. Windows `.exe` ve Android `.apk` paketleri ayrı dağıtım dosyalarıdır; Kali Linux için kaynak kod kurulumunu kullanın.

## Kali Linux kurulumu

1. Bu proje klasörünü Kali bilgisayarına aktarın.
2. Terminalde klasöre girip `chmod +x install_kali.sh run_kali.sh` komutunu çalıştırın.
3. `./install_kali.sh` komutunu çalıştırın. Python sanal ortamını ve ses/arayüz bağımlılıklarını kurar.
4. Gemini API anahtarı: `config/api_keys.json` dosyası Git tarafından izlenmediği için yeni bir kopyada bulunmayabilir. Yoksa uygulama ilk açılışta ücretsiz bir Gemini anahtarı ister ve bu dosyaya kaydeder (bir daha sormaz). Kendi anahtarını https://aistudio.google.com/apikey adresinden ücretsiz alabilirsin. `install_kali.sh` yoksa dosyayı `config/api_keys.example.json`'dan oluşturur.
5. `./run_kali.sh` ile JARVIS'i açın.

### Anonim mod (Tor)

`install_kali.sh` Tor'u ve Tor Browser'ı (`torbrowser-launcher`) kurar, Tor kontrol portunu yeni IP için ayarlar. Uygulamada "anonim mod aç" dediğinde JARVIS'in kendi web istekleri (Gemini, arama, hava durumu) Tor üzerinden gider; "yeni ip" dediğinde çıkış IP'si değişir; "anonim mod durumu" ile mevcut çıkış IP'sini görürsün. Yalnızca JARVIS'in kendi istekleri anonimleşir; tam gizlilik için tarayıcı tarafında Tor Browser kullan.

### Kali araçları

"kurulu araçlar" dediğinde JARVIS kategorili araç envanterini gösterir. Bir aracın kullanımını `tool_help` ile öğrenir, eksik aracı senin onayınla `apt` ile kurar. Gerçek tarama/testler yalnızca izinli lab hedefinde, her komut onayıyla `lab_test` üzerinden çalışır.

### Makineleri birbirine bağlama (Mesh: Windows ↔ Kali ↔ Telefon)

Birden fazla JARVIS makinen varsa (ör. Windows ana makine + Kali) birbirlerine komut verebilir. Kurulum:

1. Bir makinede JARVIS'e "mesh kur" de; sana bir **takım kodu** verir.
2. Bu kodu diğer makinenin `config/api_keys.json` dosyasına `"team_token": "<kod>"` olarak ekle (aynı kod her iki makinede olmalı).
3. Her iki makinede JARVIS'i başlat. Aynı Wi-Fi'daysalar birbirlerini otomatik bulur.

Sonrasında "Kali'de şu taramayı yap", "Windows'ta PowerPoint aç" gibi dersen JARVIS komutu doğru makineye iletir ve yanıtı sana getirir. Telefon bir makineye bağlanır; o makine gerekince komutu diğerine iletir — yani telefondan her iki bilgisayarı da yönetebilirsin. (Aynı ağda UDP 8766 ve TCP 8765 açık olmalı; Windows Güvenlik Duvarı sorarsa izin ver.)

### Windows 11 sanal makinesi (VMware, Windows ana makine)

Windows'ta çalışırken "VMware'ye Windows 11 kur" dersen, Windows 11 ISO'sunun yolunu verdiğinde JARVIS UEFI + sanal TPM 2.0 + Secure Boot ayarlı yeni bir makine oluşturup ISO'dan başlatır. ISO'yu Microsoft'un resmi sayfasından indir: https://www.microsoft.com/software-download/windows11

Kali'de JARVIS; sistem/ağ arayüzü bilgisi, seçili araçların kurulu olup olmadığı, APT paket bilgisi ve
bekleyen güncellemeleri gösterir. Gemini ve Claude, Kali'de kurulu komut satırı araçlarını `lab_test`
üzerinden kullanabilir. Yetkili test için hedefi sohbet içinde açıkça söyleyin; `lab_session` bu hedefi
`config/lab_config.json` dosyasındaki izin listesine kendisi ekler. JSON dosyasını elle düzenlemek
gerekmez. Ardından istediğiniz komut, çalıştırılmadan önce hedef ve tam komut onayıyla yürür. Komut
ve çıktı `~/JARVIS-Lab-Reports` içine kaydedilir. JARVIS yalnızca Kali'ye kurulu araçları çalıştırabilir;
kurulu olmayan bir aracı önce Kali'nin paket yöneticisiyle kurmanız gerekir.

Otomatik GitHub aktarımı için `gh auth login` ile bir kez giriş yapın ve `config/lab_config.json`
dosyasındaki `github_repo` değerini `sahip/özel-depo` biçiminde girin. JARVIS yeni depoyu özel olarak oluşturur veya var olan deponun özel
olduğunu doğrular; raporları oturum sırasında otomatik gönderir. Temel gizli bilgi taraması eşleşme
bulursa otomatik aktarımı durdurur. Bu tarama her tür gizli bilgiyi yakalamayı garanti etmez; raporları
paylaşmadan önce kontrol edin. Siber güvenlik komutlarını yalnızca kendi makinelerinizde veya açıkça
izinli eğitim laboratuvarlarında çalıştırın.

Mikrofon izni ve masaüstü oturumu gerektiğinden JARVIS'i grafik oturumu içindeki terminalden başlatın. Sesli yanıt için `ffplay` kurulum betiğine dahildir.

## Telefonda veya Windows'tan erişim

Uygulama açıkken aynı Wi-Fi ağına bağlı telefondan ya da Windows bilgisayardan, ekranda gösterilen IP adresi ve güvenlik koduyla bağlanın. Gelen istekler JARVIS'in mevcut Gemini/yerel sağlayıcısından yürütülür. Başka bir ağdan erişim için ayrıca `cloudflared` kurup PATH'e ekleyin; JARVIS kuruluysa mevcut tünel desteğini kullanır. Güvenlik kodu ayar dosyasında tutulur; dışarıya açık tünel URL'sini ve kodu başkalarıyla paylaşmayın.

## Özellik ve platform notu

Sohbet, mikrofon, hatırlatıcılar ve telefon üzerinden soru sorma Kali'de çalışacak şekilde hazırlanmıştır. Fare/klavye kontrolü ve bazı uygulama entegrasyonları Windows'a özgü API ve uygulamalara dayanır; Kali'de bu Windows özelliklerinin tümü mevcut olmayabilir. Görsel/video araçları işletim sisteminde bulunan dosya konumları ve yazı tiplerini kullanır.

## Windows ve Android

Windows'ta `JARVIS Ucretsiz.exe` çalıştırılabilir. Android'de `JARVIS_Ucretsiz_Telefon.apk` telefona kurulur. Kali'den erişim için Android istemcisi, uygulama açık olan Kali bilgisayarının IP/port bilgilerine bağlanmalıdır.

## Anahtar güvenliği

`config/api_keys.json` Git tarafından izlenmez. Anahtarın yanlışlıkla herkese açık bir yerde paylaşıldığını düşünüyorsanız Google AI Studio'dan iptal edip yenisini oluşturun.
