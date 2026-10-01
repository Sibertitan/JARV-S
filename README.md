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
2. Bu kodu diğer makinenin `config/api_keys.json` dosyasına `"team_token": "<kod>"` olarak ekle (aynı kod her iki makinede olmalı). Makineler birbirini bu kodla imzalanmış yayınlarla bulur; kodu bilmeyen bir cihaz kendini eş olarak tanıtamaz.
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

Uygulama açıkken aynı Wi-Fi ağına bağlı telefondan ya da Windows bilgisayardan, ekranda gösterilen IP adresi ve güvenlik koduyla bağlanın. Gelen istekler JARVIS'in mevcut Gemini/yerel sağlayıcısından yürütülür. Başka bir ağdan erişim için ayrıca `cloudflared` kurup PATH'e ekleyin ve `config/api_keys.json` içine `"web_remote_access": true` yazın. Tünel bu ayar olmadan açılmaz, çünkü tam araçlı JARVIS'i internete açar. Güvenlik kodu ayar dosyasında tutulur; dışarıya açık tünel URL'sini ve kodu başkalarıyla paylaşmayın.

## Özellik ve platform notu

Sohbet, mikrofon, hatırlatıcılar ve telefon üzerinden soru sorma Kali'de çalışacak şekilde hazırlanmıştır. Fare/klavye kontrolü ve bazı uygulama entegrasyonları Windows'a özgü API ve uygulamalara dayanır; Kali'de bu Windows özelliklerinin tümü mevcut olmayabilir. Görsel/video araçları işletim sisteminde bulunan dosya konumları ve yazı tiplerini kullanır.

## Windows ve Android

Windows'taki özgün `JARVIS Ucretsiz.exe` dosyası korunmuştur. Güncel kaynaklardan üretilen Windows paketi `JARVIS Integrated 2026-09-30 v3.exe` dosyasıdır. Android'de JARVIS istemcisi `android/app/build/outputs/apk/debug/app-debug.apk` konumundadır. İstemci Gemini anahtarını telefona kopyalamaz; açık ve ağa erişilebilir bir Windows/Kali JARVIS bilgisayarına bağlanır. Aynı Wi-Fi'da bilgisayarın yerel IP/port bilgisini kullanın. Dış ağ erişimi için bilgisayarda güvenli biçimde yapılandırılmış tünel gerekir.

Android APK bir masaüstü eşlikçi istemcisidir; Windows/Kali uygulamasındaki fare-klavye ve yerel dosya özelliklerini Android'in içinde çalıştırmaz. APK debug imzasıyla derlenip Android 35 emülatörüne kuruldu; JARVIS `/ping` ve çevrimdışı test yanıtıyla `/ask` bağlantısı doğrulandı. Fiziksel telefon ve gerçek Wi-Fi yönlendirici testi yapılmadı. Kali araçları Linux'a özgüdür; Windows `.exe` veya Android APK içine taşınamaz ve üç platformda aynı yerel araçların bulunması garanti edilemez.

Android istemcisinin kaynak projesi `android/` klasöründedir. Güncel APK'yı üretmek için bu klasörü Android Studio ile açın veya Android SDK Platform 35 kurulu bir makinede `gradlew assembleDebug` çalıştırın. İstemci aynı Wi-Fi üzerindeki Windows/Kali JARVIS sunucusuna bağlanır; Gemini anahtarı yalnızca bilgisayardaki `config/api_keys.json` dosyasında kalır. Yeni istemci APK'sı eski APK'nın üzerine kurulmak yerine ayrı uygulama olarak kurulabilir.

Windows kaynak paketi `JARVIS Integrated 2026-09-30 v3.exe`, Android debug paketi `android/app/build/outputs/apk/debug/app-debug.apk` konumundadır. Bunlar özgün Windows EXE'si ve telefondaki APK'nın üzerine yazmaz. Android paketi test/debug imzası kullanır; mağaza veya genel dağıtım sürümü değildir.

Windows paketi `--self-test` parametresiyle açılırsa arayüz, mikrofon, telefon sunucusu veya tünel başlatmadan Headroom'u ve yapılandırılmış MCP sunucularını kontrol eder. İşlem başarılıysa `0`, başarısızsa sıfır dışı çıkış kodu döner.

Kali kurulum betiği temel uygulama bağımlılıklarına ek olarak yalnızca savunma/adli inceleme araçlarının sınırlı bir listesini kurar. `kali-linux-everything`, ağ saldırısı, parola kırma ve istismar framework'leri topluca kurulmaz veya JARVIS araç listesine açılmaz. Bu nedenle Kali'nin bütün framework'lerinin bulunduğu iddia edilmez.

## OmniRoute ve yerel MCP sunucuları

OmniRoute isteğe bağlı, bilgisayarda çalışan bir ağ geçididir; kendi başına model veya ücretsiz kota sağlamaz. Node.js desteklenen bir sürümle yerel OmniRoute kurup `omniroute` ile başlatın. Dashboard/API varsayılan olarak `http://127.0.0.1:20128` üzerinde kalmalıdır; dış ağa açmayın. OmniRoute dashboard'unda Gemini sağlayıcısına JARVIS'te zaten kullandığınız aynı Gemini API anahtarını ekleyin. OmniRoute bu sağlayıcı kimlik bilgisini kendi yerel veritabanında ayrıca saklar; yeni bir Gemini anahtarı gerekmez.

JARVIS `config/api_keys.json` ayarına `omniroute_url` (ör. `http://127.0.0.1:20128/v1`) ve isteğe bağlı `omniroute_model` (varsayılan `auto`) eklenebilir. `switch_brain` aracıyla OmniRoute'a geçilebilir; URL ayarlıysa Gemini kota hatasında da yerel OmniRoute'a bir kez yönelmeyi dener. Bu istek yine Gemini'nin çevrimiçi servisine gider ve aynı kota/şartlara tabidir. Üçüncü taraf ücretsiz sağlayıcılar ayrıca hesap, oturum veya kendi limitlerini gerektirebilir; otomatik ya da sınırsız ücretsiz çalışma garantisi yoktur. OmniRoute JARVIS'in EXE/APK dosyalarına gömülmez.

JARVIS, MCP araçlarını model isteğine yüzlerce şema eklemeden yerel olarak arar ve gereken aracı çağırır. OmniRoute MCP bağlantısı `omniroute_mcp_stdio.mjs` yerel başlatıcısını kullanır; kurulumdaki Node.js ve OmniRoute paket yollarını `config/mcp_servers.json` içinde ayarlayın. Bu başlatıcı, Türkçe karakter/boşluk içeren Windows yollarında resmi CLI başlatıcısının kapanması sorununu aşar ve OmniRoute'un MCP stdout korumasını yükler. OmniRoute ağ geçidi yerelde çalışmalıdır. Salt-okunur MCP araçları çağrılabilir; yazma/değiştirme araçları yerel onay ister.

## Kalıcı oturum hafızası ve kendini geliştirme

JARVIS, [claude-mem](https://github.com/thedotmack/claude-mem) fikrini yerel olarak uygular: uzun ya da önemli bir işi bitirince `remember_session` ile 1-3 cümlelik bir oturum özeti `memory/session_memory.jsonl` dosyasına yazılır. Bu özetler bir sonraki açılışta konuşma bağlamına otomatik geri yüklenir; `recall_sessions` ile de aranabilir. Böylece kaldığımız yerden devam edilebilir.

Ayrıca [one-skill-to-rule-them-all / task-observer](https://github.com/rebelytics/one-skill-to-rule-them-all) fikri yerel bir gözlem günlüğü olarak eklendi: kullanıcı düzeltmesi, yinelenen tercih/iş ya da bir eksik fark edildiğinde `observe_self` ile `memory/observations.jsonl` dosyasına sessizce not düşülür; `review_observations` ile gözden geçirilir. Amaç JARVIS'in zamanla daha isabetli çalışması. Her iki günlük de yereldir, `memory/` klasörü Git tarafından izlenmez ve dış bir servise gönderilmez.

[claude-code-setup](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-code-setup) eklentisi Claude Code'a özgü olduğundan JARVIS'e doğrudan kurulamaz; fikri (projeyi inceleyip kişiye özel otomasyon önerileri sunmak, salt okunur) `recommend_setup` aracı olarak yerel biçimde uygulandı. Bu araç JARVIS'in kendi ortamını (sağlayıcı anahtarı, OmniRoute yedeği, MCP yapılandırması, oturum hafızası kullanımı, anımsatıcı/zamanlı görevler, çevrimdışı Vosk modeli ve Linux'ta Tor/Kali araçları) inceleyip önceliklendirilmiş, uygulanabilir öneriler döndürür; hiçbir ayarı kendiliğinden değiştirmez. "Kendini kur / ne eksik / kurulumumu iyileştir" dediğinde çalışır.

## Yerleşik kod ajanı (codex)

JARVIS'in kendi kod yazıcısı vardır ve ücretsiz Gemini beyniyle çalışır. `code_run` aracı verilen kodu bir dosyaya yazar, **çalıştırır** ve çıktısını (stdout + stderr + çıkış kodu) geri döndürür; böylece JARVIS yaz → çalıştır → hatayı gör → düzelt döngüsüyle çalışan program üretir. Python, Node.js, bash ve PowerShell desteklenir; hem Windows hem Kali/Linux'ta yereldir, ek API gerektirmez. Kod çalıştırma her seferinde kullanıcı onayı ister. Uygulama/oyun gibi çok dosyalı projeler için `write_project_file` + `run_project`, GitHub'a yükleme için `github` aracı vardır.

## Telefondan iki işletim sistemini de yönetme

Android APK ince bir istemcidir: yazdığın komutu aynı Wi-Fi'daki JARVIS bilgisayarına `/ask` ile iletir. Bu istek **tam araçlı ajanı** çalıştırır (ücretsiz Gemini modu dahil), yani telefondan bilgisayarın tüm yeteneklerini kullanırsın: uygulama açma, ekran kontrolü, kod yazma/çalıştırma, dosya işlemleri ve Kali'de yetkili `lab_test`. JARVIS Windows'ta çalışıyorsa telefondan Windows'u, Kali'de çalışıyorsa Kali'yi yönetirsin. Mesh açıkken bağlandığın makine komutu diğerine iletebildiği için tek telefondan hem Windows hem Kali'ye erişebilirsin.

## DaVinci Resolve MCP

Bu Windows kopyasında [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) kaynakları `work/davinci-resolve-mcp/` altında bulunur ve gizli `config/mcp_servers.json` ayarı bu bilgisayardaki Python'a göre hazırlanmıştır; sunucu 37 aracı keşfetti ve Resolve'u başlatmayan `runtime_mode` çağrısı doğrulandı. Linux/Kali kopyasında depoyu ve MCP Python bağımlılıklarını kurup `config/mcp_servers.example.json` içindeki komut/yolları uyarlayın. Harici betikleme API'si Resolve sürümü/edition ve ayarlarına bağlıdır; canlı düzenleme bu ortamda doğrulanmadı. Yalnızca güvendiğiniz yerel MCP sunucularını yapılandırın.

## Anahtar güvenliği

`config/api_keys.json` Git tarafından izlenmez. Anahtarın yanlışlıkla herkese açık bir yerde paylaşıldığını düşünüyorsanız Google AI Studio'dan iptal edip yenisini oluşturun.
