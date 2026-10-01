# Midas modülü — yalnızca simülasyon

## Ne kontrol edildi (2026-10-01)

- Midas'ın resmi sitesi ve `llms.txt` dosyası (https://www.getmidas.com/llms.txt) bir mobil yatırım
  uygulamasını anlatıyor; herkese açık API, geliştirici programı ya da resmi programatik hesap erişimi
  belgelenmiyor.
- Bulunan tek programatik entegrasyon **resmi olmayan, üçüncü taraf** bir MCP sunucusu
  (https://glama.ai/mcp/servers/gmeff5y4zw). Kendi açıklamasına göre: "Midas has no public API",
  "Unofficial, not affiliated with or endorsed by Midas"; web uygulamasını Playwright ile sürüp belgelenmemiş
  iç GraphQL çağrılarını tekrarlıyor ve gerçek parayla emir veriyor.

## Karar

JARVIS belgelenmemiş uç noktaları kullanmaz, uygulamayı kazımaz, MFA/CAPTCHA/anti-bot korumalarını aşmaz.
`jarvis_midas.py` iki mod sunar:

| Mod | Davranış |
|---|---|
| `SIMULATION` (varsayılan) | Sentetik piyasa (`SIM.*` semboller), emir kuralları, masaüstü onayı, simüle gerçekleşme |
| `READ_ONLY` | Simüle okuma; tüm emirler reddedilir |
| `LIVE` | Reddedilir (`MidasError`) |

Kodla zorlanan kurallar: `AUTO_EXECUTION = False` sabit; her emir `BEKLIYOR` başlar; onay JARVIS masaüstü
penceresinden verilir (modelin ya da telefondan gelen isteğin kendisi onaylayamaz); onay anında emir yeniden
doğrulanır; açığa satış yok; emir değeri ve adet üst sınırı; her işlem `memory/midas_audit.jsonl` dosyasına
yazılır. Durum `memory/midas_sim.json` dosyasında tutulur (Git tarafından izlenmez).

Ayarlar (`config/api_keys.json`): `"midas_mode": "SIMULATION" | "READ_ONLY"`, `"midas_max_order_value": 10000`.

## Canlı erişim neye ihtiyaç duyar

1. Resmi bir Midas API'si / veri dışa aktarımı ya da Midas'ın yazılı izni; veya kullanıcının kendi cihazında,
   kendi oturumuyla ve kendisi başındayken çalışma.
2. Giriş, MFA ve CAPTCHA'yı kullanıcının kendisi yapması. JARVIS parola, MFA kodu, çerez veya oturum
   anahtarı saklamaz.
3. Önce salt okunur; her emir sembol, yön, adet, fiyat ve değerle gösterilip yalnızca o emre özel açık
   onayla yürütülmeli.
